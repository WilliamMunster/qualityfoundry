"""QualityFoundry - Orchestration API Routes (PR-4)

编排执行 API：统一的测试执行入口，集成工具层、证据链和门禁决策。

POST /api/v1/orchestrations/run
- 接收自然语言输入或结构化选项
- 执行工具（pytest/playwright等）
- 收集证据并生成 evidence.json
- 执行门禁决策（PASS/FAIL/NEED_HITL）
- 返回决策、证据和链接
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.audit_log_models import AuditEventType, AuditLog
from qualityfoundry.governance import (
    GateDecision,
    GateResult,
    TraceCollector,
    evaluate_gate_with_hitl,
)
from qualityfoundry.services.approval_service import ApprovalService
from qualityfoundry.tools import ToolRequest, ToolResult, ToolStatus
from qualityfoundry.tools.registry import get_registry, ToolNotFoundError

# 导入 runners 模块以自动注册工具
import qualityfoundry.tools.runners  # noqa: F401

router = APIRouter(prefix="/orchestrations", tags=["orchestrations"])


# ============== Request/Response Models ==============


class OrchestrationOptions(BaseModel):
    """执行选项（可控模式，用于 smoke 测试）"""

    tool_name: str = Field(default="run_pytest", description="要执行的工具名称")
    args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    timeout_s: int = Field(default=120, ge=1, le=3600, description="超时时间（秒）")
    dry_run: bool = Field(default=False, description="是否为干运行模式")


class OrchestrationRequest(BaseModel):
    """编排执行请求"""

    nl_input: str = Field(..., description="自然语言输入描述")
    environment_id: Optional[UUID] = Field(default=None, description="环境 ID")
    options: Optional[OrchestrationOptions] = Field(
        default=None,
        description="执行选项（优先于 NL 解析，用于确定性测试）",
    )


class OrchestrationLinks(BaseModel):
    """执行结果链接"""

    execution_id: Optional[UUID] = Field(default=None, description="执行记录 ID")
    approval_id: Optional[UUID] = Field(default=None, description="审批记录 ID（NEED_HITL 时）")
    report_url: Optional[str] = Field(default=None, description="证据报告下载 URL")


class OrchestrationResponse(BaseModel):
    """编排执行响应"""

    run_id: UUID = Field(..., description="运行 ID")
    decision: GateDecision = Field(..., description="门禁决策")
    reason: str = Field(..., description="决策原因")
    evidence: dict[str, Any] = Field(..., description="证据摘要")
    links: OrchestrationLinks = Field(..., description="相关链接")


class RunSummary(BaseModel):
    """运行摘要"""

    run_id: UUID = Field(..., description="运行 ID")
    started_at: datetime = Field(..., description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")
    decision: Optional[str] = Field(default=None, description="门禁决策")
    decision_source: Optional[str] = Field(default=None, description="决策来源")
    tool_count: int = Field(default=0, description="工具调用数量")


class RunsListResponse(BaseModel):
    """运行列表响应"""

    runs: list[RunSummary] = Field(..., description="运行摘要列表")
    count: int = Field(..., description="返回数量")
    total: int = Field(..., description="总数量")


# ============== Helper Functions ==============


def _build_tool_request(
    run_id: UUID,
    nl_input: str,
    options: Optional[OrchestrationOptions],
) -> ToolRequest:
    """
    构建工具请求。

    MVP 规划器：
    - 优先使用 options 指定（保证 smoke 可控）
    - 未指定则做简单 heuristic（默认跑 pytest）
    """
    if options:
        return ToolRequest(
            tool_name=options.tool_name,
            args=options.args,
            run_id=run_id,
            timeout_s=options.timeout_s,
            dry_run=options.dry_run,
        )

    # 简单启发式：根据 nl_input 关键词决定工具
    nl_lower = nl_input.lower()
    if "playwright" in nl_lower or "browser" in nl_lower or "e2e" in nl_lower:
        return ToolRequest(
            tool_name="run_playwright",
            args={},
            run_id=run_id,
            timeout_s=300,
        )

    # 默认：pytest
    return ToolRequest(
        tool_name="run_pytest",
        args={"test_path": "tests"},
        run_id=run_id,
        timeout_s=120,
    )


async def _execute_tool(request: ToolRequest) -> ToolResult:
    """执行工具并返回结果"""
    from datetime import datetime, timezone

    registry = get_registry()

    try:
        tool_func = registry.get(request.tool_name)
    except ToolNotFoundError:
        # 工具不存在，返回失败结果
        now = datetime.now(timezone.utc)
        return ToolResult(
            status=ToolStatus.FAILED,
            stdout=None,
            stderr=f"Tool not found: {request.tool_name}",
            started_at=now,
            ended_at=now,
        )

    return await tool_func(request)


def _create_approval_if_needed(
    gate_result: GateResult,
    run_id: UUID,
    db: Session,
) -> Optional[UUID]:
    """如果需要 HITL，创建审批记录"""
    if gate_result.decision != GateDecision.NEED_HITL:
        return None

    service = ApprovalService(db)
    approval = service.create_approval(
        entity_type="orchestration",
        entity_id=run_id,
        reviewer=None,  # 待分配
    )
    return approval.id


# ============== API Endpoints ==============


@router.get("/runs", response_model=RunsListResponse)
def list_runs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    列出最近的运行记录。

    从 AuditLog 聚合 run_id，返回每个运行的摘要信息。
    """
    from sqlalchemy import desc, distinct

    # 获取唯一 run_id 总数
    total_query = db.query(func.count(distinct(AuditLog.run_id)))
    total = total_query.scalar() or 0

    # 获取最近的 run_id 列表（按最新事件时间降序）
    subquery = (
        db.query(
            AuditLog.run_id,
            func.min(AuditLog.ts).label("started_at"),
            func.max(AuditLog.ts).label("finished_at"),
        )
        .group_by(AuditLog.run_id)
        .order_by(desc(func.max(AuditLog.ts)))
        .offset(offset)
        .limit(limit)
        .subquery()
    )

    # 获取每个 run 的详细信息
    runs = []
    run_ids = db.query(subquery.c.run_id, subquery.c.started_at, subquery.c.finished_at).all()

    for row in run_ids:
        run_id = row.run_id
        started_at = row.started_at
        finished_at = row.finished_at

        # 获取决策事件
        decision_event = (
            db.query(AuditLog)
            .filter(
                AuditLog.run_id == run_id,
                AuditLog.event_type == AuditEventType.DECISION_MADE,
            )
            .first()
        )

        # 统计工具调用数
        tool_count = (
            db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.run_id == run_id,
                AuditLog.event_type.in_([
                    AuditEventType.TOOL_STARTED,
                    AuditEventType.TOOL_FINISHED,
                ]),
            )
            .scalar() or 0
        ) // 2  # started + finished = 1 次调用

        runs.append(
            RunSummary(
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                decision=decision_event.status if decision_event else None,
                decision_source=decision_event.decision_source if decision_event else None,
                tool_count=tool_count,
            )
        )

    return RunsListResponse(
        runs=runs,
        count=len(runs),
        total=total,
    )


@router.post("/run", response_model=OrchestrationResponse)
async def run_orchestration(
    req: OrchestrationRequest,
    db: Session = Depends(get_db),
):
    """
    执行编排流程。

    流程：
    1. 生成 run_id
    2. 构建执行计划（优先使用 options，否则解析 nl_input）
    3. 执行工具
    4. 收集证据（写入 artifacts/{run_id}/evidence.json）
    5. 门禁决策（PASS/FAIL/NEED_HITL）
    6. 返回响应
    """
    # 1. Generate run_id
    run_id = uuid4()

    # 2. Build tool request
    tool_request = _build_tool_request(run_id, req.nl_input, req.options)

    # 3. Execute tool
    tool_result = await _execute_tool(tool_request)

    # 4. Collect evidence
    collector = TraceCollector(
        run_id=str(run_id),
        input_nl=req.nl_input,
        environment={
            "environment_id": str(req.environment_id) if req.environment_id else None,
        },
    )
    collector.add_tool_result(tool_request.tool_name, tool_result)
    evidence = collector.collect()

    # Save evidence to file
    collector.save(evidence)

    # 5. Gate decision
    gate_result = evaluate_gate_with_hitl(evidence)

    # 6. Create approval if NEED_HITL
    approval_id = None
    if gate_result.decision == GateDecision.NEED_HITL:
        try:
            approval_id = _create_approval_if_needed(gate_result, run_id, db)
        except Exception:
            # 审批创建失败不阻塞主流程
            pass

    # 7. Build response
    links = OrchestrationLinks(
        execution_id=None,  # 可扩展：关联执行记录
        approval_id=approval_id,
        report_url=f"/api/v1/artifacts/{run_id}/evidence.json",
    )

    return OrchestrationResponse(
        run_id=run_id,
        decision=gate_result.decision,
        reason=gate_result.reason,
        evidence=evidence.model_dump(),
        links=links,
    )
