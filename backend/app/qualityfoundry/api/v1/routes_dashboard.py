"""QualityFoundry - Dashboard API Routes

只读 Dashboard 聚合接口：一次请求返回 cards + trend + recent_runs。

GET /api/v1/dashboard/summary
- RBAC: RequireOrchestrationRead
- ADMIN: 额外返回 audit_summary
- Query params: days (7/30/90), limit (max 200)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, distinct, func
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from qualityfoundry.api.deps.auth_deps import get_current_user, RequireOrchestrationRead
from qualityfoundry.database.config import get_db
from qualityfoundry.database.audit_log_models import AuditEventType, AuditLog
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.governance.tracing.collector import load_evidence


router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


# ============== Response Models ==============


class DashboardCards(BaseModel):
    """Dashboard 统计卡片"""
    pass_count: int = Field(default=0, description="PASS 数量")
    fail_count: int = Field(default=0, description="FAIL 数量")
    hitl_count: int = Field(default=0, description="NEED_HITL 数量")
    avg_elapsed_ms: Optional[float] = Field(default=None, description="平均执行时间 (ms)")
    short_circuit_count: int = Field(default=0, description="短路熔断次数")
    total_runs: int = Field(default=0, description="总运行数")


class TrendPoint(BaseModel):
    """趋势数据点"""
    run_id: str = Field(..., description="Run ID (前 8 位)")
    elapsed_ms: Optional[float] = Field(default=None, description="执行时间 (ms)")
    started_at: datetime = Field(..., description="开始时间")
    decision: Optional[str] = Field(default=None, description="决策")


class RecentRunItem(BaseModel):
    """近期 Run 条目"""
    run_id: UUID = Field(..., description="运行 ID")
    started_at: datetime = Field(..., description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")
    decision: Optional[str] = Field(default=None, description="决策")
    decision_source: Optional[str] = Field(default=None, description="决策来源")
    tool_count: int = Field(default=0, description="工具调用数")
    policy_version: Optional[str] = Field(default=None, description="策略版本")
    policy_hash: Optional[str] = Field(default=None, description="策略哈希")


class AuditSummaryDTO(BaseModel):
    """审计摘要（仅 ADMIN）"""
    total_events: int = Field(default=0, description="总事件数")
    runs_with_events: int = Field(default=0, description="有事件的运行数")


class DashboardSummaryResponse(BaseModel):
    """Dashboard 聚合响应"""
    cards: DashboardCards = Field(..., description="统计卡片")
    trend: list[TrendPoint] = Field(default_factory=list, description="趋势数据")
    recent_runs: list[RecentRunItem] = Field(default_factory=list, description="近期运行")
    by_decision: dict[str, int] = Field(default_factory=dict, description="按决策分组计数")
    by_policy_hash: dict[str, int] = Field(default_factory=dict, description="按策略哈希分组计数")
    audit_summary: Optional[AuditSummaryDTO] = Field(default=None, description="审计摘要（仅 ADMIN）")


# ============== API Endpoints ==============


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    days: int = Query(default=7, ge=1, le=90, description="时间窗口（天）"),
    limit: int = Query(default=50, ge=1, le=200, description="最大返回数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireOrchestrationRead),
):
    """
    获取 Dashboard 聚合数据。
    
    返回 cards (统计卡片)、trend (趋势)、recent_runs (近期运行)、
    by_decision (按决策分组计数) 和 by_policy_hash (按策略分组计数)。
    ADMIN 用户额外返回 audit_summary。
    
    缺失值策略：
    - 无 finished_at 的 run 仍统计到 total_runs，但不进入 duration 平均值计算
    - 无 decision 的 run 不计入 by_decision
    - 无 policy_hash 的 run 不计入 by_policy_hash
    """
    # 1. 计算时间范围
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)
    
    # 2. 构建基础查询（所有权过滤 + 时间范围）
    base_query = db.query(AuditLog).filter(AuditLog.ts >= start_time)
    if current_user.role != UserRole.ADMIN:
        base_query = base_query.filter(AuditLog.created_by_user_id == current_user.id)
    
    # 3. 获取 run 列表（按最新事件时间降序，取 limit 条）
    run_subquery = (
        base_query.with_entities(
            AuditLog.run_id,
            func.min(AuditLog.ts).label("started_at"),
            func.max(AuditLog.ts).label("finished_at"),
        )
        .group_by(AuditLog.run_id)
        .order_by(desc(func.max(AuditLog.ts)))
        .limit(limit)
        .subquery()
    )
    
    run_rows = db.query(
        run_subquery.c.run_id,
        run_subquery.c.started_at,
        run_subquery.c.finished_at,
    ).all()
    
    # 4. 收集统计数据
    pass_count = 0
    fail_count = 0
    hitl_count = 0
    short_circuit_count = 0
    elapsed_values: list[float] = []
    trend_points: list[TrendPoint] = []
    recent_runs: list[RecentRunItem] = []
    by_decision: dict[str, int] = defaultdict(int)
    by_policy_hash: dict[str, int] = defaultdict(int)
    
    for row in run_rows:
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
        
        decision = decision_event.status if decision_event else None
        decision_source = decision_event.decision_source if decision_event else None
        policy_hash = decision_event.policy_hash if decision_event else None
        
        # 统计决策
        if decision:
            upper = decision.upper()
            by_decision[upper] += 1
            if upper in ("PASS", "APPROVED"):
                pass_count += 1
            elif upper in ("FAIL", "REJECTED"):
                fail_count += 1
            elif upper in ("NEED_HITL", "PENDING"):
                hitl_count += 1
        
        # 统计 policy_hash
        if policy_hash:
            by_policy_hash[policy_hash[:8]] += 1
        
        # 统计工具调用数
        tool_count = (
            db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.run_id == run_id,
                AuditLog.event_type == AuditEventType.TOOL_STARTED,
            )
            .scalar() or 0
        )
        
        # 从 evidence 读取 governance 数据
        evidence = load_evidence(run_id)
        elapsed_ms = None
        policy_version = None
        short_circuited = False
        
        if evidence:
            if evidence.governance:
                elapsed_ms = getattr(evidence.governance, 'elapsed_ms_total', None)
                short_circuited = getattr(evidence.governance, 'short_circuited', False)
                # 只有有 elapsed_ms 的才计入平均值
                if elapsed_ms is not None:
                    elapsed_values.append(elapsed_ms)
                if short_circuited:
                    short_circuit_count += 1
            
            # 尝试获取 policy version
            if evidence.policy_meta:
                policy_version = getattr(evidence.policy_meta, 'version', None)
        
        # 添加 trend 点（前 20 条）
        if len(trend_points) < 20:
            trend_points.append(TrendPoint(
                run_id=str(run_id)[:8],
                elapsed_ms=elapsed_ms,
                started_at=started_at,
                decision=decision,
            ))
        
        # 添加 recent runs（前 10 条）
        if len(recent_runs) < 10:
            recent_runs.append(RecentRunItem(
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                decision=decision,
                decision_source=decision_source,
                tool_count=tool_count,
                policy_version=policy_version,
                policy_hash=policy_hash[:8] if policy_hash else None,
            ))
    
    # 5. 计算平均执行时间（只统计有 elapsed_ms 的 run）
    avg_elapsed_ms = None
    if elapsed_values:
        avg_elapsed_ms = sum(elapsed_values) / len(elapsed_values)
    
    # 6. 构建 cards
    cards = DashboardCards(
        pass_count=pass_count,
        fail_count=fail_count,
        hitl_count=hitl_count,
        avg_elapsed_ms=avg_elapsed_ms,
        short_circuit_count=short_circuit_count,
        total_runs=len(run_rows),
    )
    
    # 7. 审计摘要（仅 ADMIN）
    audit_summary = None
    if current_user.role == UserRole.ADMIN:
        total_events = base_query.count()
        runs_with_events = db.query(func.count(distinct(AuditLog.run_id))).scalar() or 0
        audit_summary = AuditSummaryDTO(
            total_events=total_events,
            runs_with_events=runs_with_events,
        )
    
    # 8. 反转 trend 使其按时间正序
    trend_points.reverse()
    
    return DashboardSummaryResponse(
        cards=cards,
        trend=trend_points,
        recent_runs=recent_runs,
        by_decision=dict(by_decision),
        by_policy_hash=dict(by_policy_hash),
        audit_summary=audit_summary,
    )
