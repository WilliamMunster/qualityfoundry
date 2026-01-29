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

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from qualityfoundry.api.deps.auth_deps import get_current_user, RequireOrchestrationRun, RequireOrchestrationRead
from qualityfoundry.database.user_models import User, UserRole
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.audit_log_models import AuditEventType, AuditLog
from qualityfoundry.services.audit_service import write_audit_event
from qualityfoundry.governance import (
    GateDecision,
    GateResult,
    TraceCollector,
    evaluate_gate_with_hitl,
)
from qualityfoundry.services.approval_service import ApprovalService
from qualityfoundry.tools import ToolRequest, ToolResult, ToolStatus
from qualityfoundry.tools.registry import get_registry, ToolNotFoundError
from qualityfoundry.services.event_service import EventService

# 导入 runners 模块以自动注册工具
import qualityfoundry.tools.runners  # noqa: F401

router = APIRouter(
    prefix="/orchestrations",
    tags=["orchestrations"],
    dependencies=[Depends(get_current_user)],  # 整个 router 需要认证
)


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


# ============== P1: RunDetail DTO ==============


class OwnerInfo(BaseModel):
    """所有者信息"""
    user_id: Optional[UUID] = Field(default=None, description="用户 ID")
    username: Optional[str] = Field(default=None, description="用户名")


class PolicyMeta(BaseModel):
    """策略元数据"""
    version: Optional[str] = Field(default=None, description="策略版本")
    hash: Optional[str] = Field(default=None, description="策略哈希")


class ReproMetaDTO(BaseModel):
    """可复现性元数据"""
    git_sha: Optional[str] = Field(default=None, description="Git SHA")
    git_branch: Optional[str] = Field(default=None, description="分支")
    git_dirty: bool = Field(default=False, description="是否有未提交变更")
    deps_fingerprint: Optional[str] = Field(default=None, description="依赖指纹")


class GovernanceDTO(BaseModel):
    """治理元数据"""
    budget: dict[str, Any] = Field(default_factory=dict, description="预算信息")
    short_circuited: bool = Field(default=False, description="是否提前熔断")
    short_circuit_reason: Optional[str] = Field(default=None, description="熔断原因")
    decision_source: Optional[str] = Field(default=None, description="决策来源")


class ArtifactInfo(BaseModel):
    """产物信息"""
    type: str = Field(..., description="产物类型")
    path: str = Field(..., description="相对路径")
    size: Optional[int] = Field(default=None, description="文件大小")
    mime: Optional[str] = Field(default=None, description="MIME 类型")


class AuditSummary(BaseModel):
    """审计摘要（仅 ADMIN 可见）"""
    event_count: int = Field(default=0, description="事件数量")
    first_at: Optional[datetime] = Field(default=None, description="首个事件时间")
    last_at: Optional[datetime] = Field(default=None, description="最后事件时间")


class SummaryInfo(BaseModel):
    """运行摘要信息"""
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")
    ok: Optional[bool] = Field(default=None, description="是否成功")
    decision: Optional[str] = Field(default=None, description="门禁决策")
    tool_count: int = Field(default=0, description="工具调用数量")


class ArtifactAuditSummary(BaseModel):
    """产物审计汇总 (L5 Dashboard)"""
    total_count: int = Field(..., description="总产物数量")
    stats_by_type: dict[str, int] = Field(..., description="按类型统计")
    truncated: bool = Field(..., description="是否截断示例")
    boundary: dict[str, Any] = Field(..., description="收集边界 (scope/extensions)")
    samples: list[dict[str, Any]] = Field(default_factory=list, description="产物样本预览")


class RunDetail(BaseModel):
    """运行详情 DTO (P1)"""
    run_id: UUID = Field(..., description="运行 ID")
    owner: Optional[OwnerInfo] = Field(default=None, description="所有者信息")
    summary: SummaryInfo = Field(..., description="运行摘要")
    policy: Optional[PolicyMeta] = Field(default=None, description="策略元数据")
    repro: Optional[ReproMetaDTO] = Field(default=None, description="可复现性元数据")
    governance: Optional[GovernanceDTO] = Field(default=None, description="治理元数据")
    artifacts: list[ArtifactInfo] = Field(default_factory=list, description="产物列表")
    artifact_audit: Optional[ArtifactAuditSummary] = Field(default=None, description="产物审计汇总")
    audit_summary: Optional[AuditSummary] = Field(default=None, description="审计摘要（仅 ADMIN）")


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
        actual_tool_name = options.tool_name
        args = options.args.copy()

        # 显式映射：将 "playwright" UI 选项映射到 run_pytest 指令
        if actual_tool_name == "playwright":
            actual_tool_name = "run_pytest"
            # 如果未指定测试路径，默认为 tests/ui
            if "test_path" not in args:
                args["test_path"] = "tests/ui"

        return ToolRequest(
            tool_name=actual_tool_name,
            args=args,
            run_id=run_id,
            timeout_s=options.timeout_s,
            dry_run=options.dry_run,
        )

    # 简单启发式：默认跑 pytest
    return ToolRequest(
        tool_name="run_pytest",
        args={"test_path": "tests"},
        run_id=run_id,
        timeout_s=120,
    )


async def _execute_tool(request: ToolRequest) -> ToolResult:
    """执行工具并返回结果"""
    from datetime import datetime, timezone
    from qualityfoundry.governance.policy_loader import get_policy
    from qualityfoundry.tools.runners import register_all_tools
    
    # 确保工具已注册（registry 可能在测试期间被 reset）
    register_all_tools()

    registry = get_registry()
    policy = get_policy()

    try:
        # 使用 registry.execute 以启用 policy (sandbox/allowlist)
        return await registry.execute(request.tool_name, request, policy=policy)
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
    current_user: User = Depends(RequireOrchestrationRead),  # 权限检查
):
    """
    列出最近的运行记录。

    从 AuditLog 聚合 run_id，返回每个运行的摘要信息。
    非 ADMIN 用户只能看到自己创建的运行记录。
    """
    from sqlalchemy import desc, distinct

    # 构建基础查询（所有权过滤）
    base_query = db.query(AuditLog)
    if current_user.role != UserRole.ADMIN:
        # 非 ADMIN 只能看自己的 run
        base_query = base_query.filter(AuditLog.created_by_user_id == current_user.id)

    # 获取唯一 run_id 总数
    total_query = base_query.with_entities(func.count(distinct(AuditLog.run_id)))
    total = total_query.scalar() or 0

    # 获取最近的 run_id 列表（按最新事件时间降序）
    subquery = (
        base_query.with_entities(
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


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: UUID,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireOrchestrationRead),
):
    """
    SSE 事件流 (Dashboard P3 MVP)。
    
    支持 Last-Event-ID 补发历史事件。
    """
    async def event_generator():
        service = EventService(db)
        
        # 记录已发送的事件 ID，避免重复
        sent_ids = set()
        
        # 1. 补发历史事件
        history = service.get_events(run_id, last_event_id)
        for event in history:
            yield f"id: {event.id}\nevent: {event.event_type}\ndata: {event.data or '{}'}\n\n"
            sent_ids.add(str(event.id))
        
        # 2. 持续循环监听新事件 (MVP 简易实现：持续轮询 DB)
        try:
            while True:
                # 检查最新事件
                all_events = service.get_events(run_id)
                new_events = [e for e in all_events if str(e.id) not in sent_ids]
                
                for event in new_events:
                    yield f"id: {event.id}\nevent: {event.event_type}\ndata: {event.data or '{}'}\n\n"
                    sent_ids.add(str(event.id))

                # 如果 run 已经结束，且没有新事件，则退出循环
                from qualityfoundry.database.audit_log_models import AuditLog, AuditEventType
                is_decided = db.query(AuditLog).filter(
                    AuditLog.run_id == run_id,
                    AuditLog.event_type == AuditEventType.DECISION_MADE
                ).first()
                
                if is_decided and not new_events:
                    break
                
                # 每秒轮询一次新事件
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            # 客户端断开连接
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run_detail(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireOrchestrationRead),
):
    """
    获取运行详情（P1 RunDetail DTO）。
    
    从 AuditLog 和 evidence.json 构建完整详情。
    非 ADMIN 用户只能访问自己创建的运行记录。
    """
    from qualityfoundry.governance.tracing.collector import load_evidence
    from qualityfoundry.governance.policy_loader import get_policy
    
    # 1. 检查 run 是否存在（从 AuditLog 查）
    first_event = db.query(AuditLog).filter(AuditLog.run_id == run_id).first()
    if not first_event:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    
    # 2. 权限检查：owner filter
    owner_user_id = first_event.created_by_user_id
    if current_user.role != UserRole.ADMIN:
        if owner_user_id is None or owner_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此运行记录")
    
    # 3. 获取 owner 信息
    owner_info = None
    if owner_user_id:
        owner_user = db.query(User).filter(User.id == owner_user_id).first()
        if owner_user:
            owner_info = OwnerInfo(user_id=owner_user.id, username=owner_user.username)
    
    # 4. 从 AuditLog 聚合基础信息
    events = db.query(AuditLog).filter(AuditLog.run_id == run_id).order_by(AuditLog.ts.asc()).all()
    
    first_event = events[0] if events else None
    started_at = first_event.ts if first_event else None
    finished_at = events[-1].ts if events else None
    
    # 查找决策事件
    decision_event = next(
        (e for e in events if e.event_type == AuditEventType.DECISION_MADE),
        None
    )
    
    # 统计工具调用数
    tool_count = sum(1 for e in events if e.event_type == AuditEventType.TOOL_STARTED)
    
    # 5. 从 evidence.json 读取 policy/repro/governance
    evidence = load_evidence(run_id)
    
    policy_meta = None
    repro_meta = None
    governance_dto = None
    artifacts = []
    ok = None
    
    if evidence:
        # Policy（从当前策略获取，evidence 中可能没有）
        try:
            policy = get_policy()
            policy_meta = PolicyMeta(
                version=getattr(policy, 'version', None),
                hash=first_event.policy_hash if first_event else None,
            )
        except Exception:
            policy_meta = PolicyMeta(hash=first_event.policy_hash if first_event else None)
        
        # Repro
        if evidence.repro:
            repro_meta = ReproMetaDTO(
                git_sha=evidence.repro.git_sha,
                git_branch=evidence.repro.git_branch,
                git_dirty=evidence.repro.git_dirty or False,
                deps_fingerprint=evidence.repro.deps_fingerprint,
            )
        
        # Governance
        if evidence.governance:
            governance_dto = GovernanceDTO(
                budget=evidence.governance.budget,
                short_circuited=evidence.governance.short_circuited,
                short_circuit_reason=evidence.governance.short_circuit_reason,
                decision_source=evidence.governance.decision_source,
            )
        
        # Artifacts
        for art in evidence.artifacts:
            artifacts.append(ArtifactInfo(
                type=art.get("type", "unknown"),
                path=art.get("path", ""),
                size=art.get("size"),
                mime=art.get("mime"),
            ))
        
        # Ok status from summary
        if evidence.summary:
            ok = evidence.summary.failures == 0 and evidence.summary.errors == 0
    
    # 6. 从审计日志聚合产物汇总 (PR-Dashboard)
    from qualityfoundry.services.audit_service import get_latest_artifact_audit
    artifact_audit_data = get_latest_artifact_audit(db, run_id)
    artifact_audit_summary = None
    if artifact_audit_data:
        artifact_audit_summary = ArtifactAuditSummary(**artifact_audit_data)
    
    # 7. 审计摘要（仅 ADMIN）
    audit_summary = None
    if current_user.role == UserRole.ADMIN:
        audit_summary = AuditSummary(
            event_count=len(events),
            first_at=started_at,
            last_at=finished_at,
        )
    
    # 8. 构建返回
    return RunDetail(
        run_id=run_id,
        owner=owner_info,
        summary=SummaryInfo(
            started_at=started_at,
            finished_at=finished_at,
            ok=ok,
            decision=decision_event.status if decision_event else None,
            decision_source=decision_event.decision_source if decision_event else None,
            tool_count=tool_count,
        ),
        policy=policy_meta,
        repro=repro_meta,
        governance=governance_dto,
        artifacts=artifacts,
        artifact_audit=artifact_audit_summary,
        audit_summary=audit_summary,
    )


@router.post("/run", response_model=OrchestrationResponse)
async def run_orchestration(
    req: OrchestrationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireOrchestrationRun),  # 权限检查
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
    event_service = EventService(db)
    event_service.emit_event(run_id, "run.started", {"nl_input": req.nl_input})

    # 2. Build tool request
    tool_request = _build_tool_request(run_id, req.nl_input, req.options)

    # Record tool start
    write_audit_event(
        db,
        run_id=run_id,
        event_type=AuditEventType.TOOL_STARTED,
        user_id=current_user.id,  # 记录操作用户
        tool_name=tool_request.tool_name,
        args=tool_request.args,
        actor="orchestrator",
    )

    # 3. Execute tool
    tool_result = await _execute_tool(tool_request)

    # Record tool finish
    write_audit_event(
        db,
        run_id=run_id,
        event_type=AuditEventType.TOOL_FINISHED,
        user_id=current_user.id,  # 记录操作用户
        tool_name=tool_request.tool_name,
        status=tool_result.status.value,
        duration_ms=tool_result.duration_ms,
        actor="orchestrator",
    )

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
    event_service.emit_event(run_id, "run.finished")

    # 5. Gate decision
    gate_result = evaluate_gate_with_hitl(evidence)

    # Record decision
    write_audit_event(
        db,
        run_id=run_id,
        event_type=AuditEventType.DECISION_MADE,
        user_id=current_user.id,  # 记录操作用户
        status=gate_result.decision.value,
        decision_source="gate_evaluator",
        actor="orchestrator",
        details={"reason": gate_result.reason},
    )
    event_service.emit_event(run_id, "run.decided", {"decision": gate_result.decision.value})

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
