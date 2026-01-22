"""QualityFoundry - 编排服务 (L2 编排层)

Phase 1.2: 具备 LangGraph 节点边界的服务抽象。

设计决策：
- 依赖注入：数据库必选，注册表/收集器/策略可选（便于测试）
- 返回类型：OrchestrationResult（领域对象，无 HTTP 概念）
- 输入：OrchestrationRequest (API DTO) + 内部归一化
- 节点方法：_load_policy, _plan_tool_request, _execute_tools, _collect_evidence, _gate_and_hitl
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from operator import add
from typing import Annotated, Any, Callable, Protocol, TypedDict
from uuid import UUID

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from qualityfoundry.governance import GateDecision, evaluate_gate
from qualityfoundry.governance.gate import GateResult
from qualityfoundry.governance.tracing.collector import Evidence
from qualityfoundry.governance.policy_loader import get_policy, PolicyConfig
from qualityfoundry.governance.tracing.collector import TraceCollector
from qualityfoundry.services.approval_service import ApprovalService
from qualityfoundry.tools.contracts import ToolRequest, ToolResult
from qualityfoundry.tools.registry import get_registry, ToolRegistry


@dataclass(frozen=True)
class OrchestrationInput:
    """内部归一化输入（与 API DTO 解耦）。"""
    nl_input: str
    environment_id: UUID | None
    tool_name: str
    tool_args: dict[str, Any]
    timeout_s: int
    dry_run: bool


@dataclass(frozen=True)
class OrchestrationResult:
    """服务返回类型（领域对象，无 HTTP 概念）。"""
    run_id: UUID
    decision: GateDecision
    reason: str
    evidence: dict[str, Any]
    execution_id: UUID | None = None
    approval_id: UUID | None = None
    report_path: Path | None = None


class OrchestrationState(TypedDict, total=False):
    """通过节点方法传递的可变状态（适配 LangGraph）。"""
    run_id: UUID
    input: OrchestrationInput
    policy: PolicyConfig
    policy_meta: dict[str, Any]
    tool_request: ToolRequest
    tool_result: ToolResult
    evidence: dict[str, Any]
    decision: GateDecision
    reason: str
    approval_id: UUID | None
    report_path: Path | None


class GovernanceBudget(TypedDict, total=False):
    """成本治理预算追踪 (Phase 5.1)。

    追踪一次运行中所有工具执行累计的资源使用情况。
    用于在超出预算时进行短路决策。
    """
    elapsed_ms_total: int
    attempts_total: int
    retries_used_total: int
    short_circuited: bool
    short_circuit_reason: str | None


class LangGraphState(TypedDict, total=False):
    """LangGraph 工作流状态。

    为了兼容性，这取代了 OrchestrationState。
    所有字段都是可选的（total=False），以允许增量构建。
    """
    run_id: UUID
    input: OrchestrationInput
    policy: PolicyConfig
    policy_meta: dict[str, Any]
    tool_request: ToolRequest
    tool_result: ToolResult
    evidence: dict[str, Any]
    decision: GateDecision
    reason: str
    approval_id: UUID | None
    report_path: Path | None
    # 未来：累积消息历史
    messages: Annotated[list[str], add]
    # 成本治理 (Phase 5.1)
    budget: GovernanceBudget


# 收集器工厂类型别名（便于测试）
CollectorFactory = Callable[[UUID, str, dict[str, Any]], TraceCollector]


def _default_collector_factory(run_id: UUID, input_nl: str, environment: dict[str, Any]) -> TraceCollector:
    """默认工厂创建真实的 TraceCollector。"""
    return TraceCollector(run_id=str(run_id), input_nl=input_nl, environment=environment)


class OrchestrationRequestProtocol(Protocol):
    """编排请求协议（避免循环引用）。"""
    nl_input: str
    environment_id: UUID | None
    options: Any  # OrchestrationOptions 或 None


class OrchestratorService:
    """具备 LangGraph 节点边界的编排服务。

    依赖注入：
    - db：必选（用于 ApprovalService）
    - registry：可选（默认：全局单例）
    - collector_factory：可选（默认：创建真实的 TraceCollector）
    - policy_loader：可选（默认：从文件加载）
    """

    def __init__(
        self,
        db: Session,
        *,
        registry: ToolRegistry | None = None,
        collector_factory: CollectorFactory | None = None,
        policy_loader: Callable[[], PolicyConfig] | None = None,
        gate_evaluator: Callable[[Evidence, PolicyConfig | None], GateResult] | None = None,
    ):
        self._db = db
        self._registry = registry
        self._collector_factory = collector_factory or _default_collector_factory
        self._policy_loader = policy_loader or get_policy
        self._gate_evaluator = gate_evaluator or evaluate_gate
        self._approval_service = ApprovalService(db)

    @property
    def registry(self) -> ToolRegistry:
        """延迟访问注册表（允许在测试中进行延迟绑定）。"""
        return self._registry or get_registry()

    async def run(self, req: OrchestrationRequestProtocol) -> OrchestrationResult:
        """使用 LangGraph 执行编排流水线。

        流水线：归一化 → 加载策略 → 规划 → 执行 → 收集 → 门禁

        此方法现在内部使用 LangGraph 进行执行，
        以支持未来的动态路由和条件分支。

        返回：
            包含决策、原因、证据及可选审批 ID 的 OrchestrationResult
        """
        # 委托给基于图的实现
        return await self.run_with_graph(req)

    async def run_with_graph(self, req: OrchestrationRequestProtocol) -> OrchestrationResult:
        """使用 LangGraph 状态机执行编排。

        这是 run() 的 LangGraph 驱动版本。
        行为应与 run() 相同，但使用 StateGraph 进行执行。

        返回：
            包含决策、原因、证据及可选审批 ID 的 OrchestrationResult
        """
        from uuid import uuid4

        # 生成 run_id
        run_id = uuid4()

        # 归一化输入
        normalized_input = self._normalize_input(req)

        # 构建初始状态
        initial_state: LangGraphState = {
            "run_id": run_id,
            "input": normalized_input,
            "messages": [],
        }

        # 构建并运行图
        graph = build_orchestration_graph(self)

        # LangGraph invoke - 自动处理异步节点
        final_state = await graph.ainvoke(initial_state)

        # 从最终状态构建结果
        return OrchestrationResult(
            run_id=run_id,
            decision=final_state["decision"],
            reason=final_state["reason"],
            evidence=final_state["evidence"],
            approval_id=final_state.get("approval_id"),
            report_path=final_state.get("report_path"),
        )

    def _normalize_input(self, req: OrchestrationRequestProtocol) -> OrchestrationInput:
        """将 API DTO 转换为内部归一化输入。

        优先级：
        1. 如果提供了选项，则直接使用它们（确定性模式）
        2. 否则，根据 nl_input 关键字使用简单的启发式规则
        """
        if req.options:
            return OrchestrationInput(
                nl_input=req.nl_input,
                environment_id=req.environment_id,
                tool_name=req.options.tool_name,
                tool_args=req.options.args,
                timeout_s=req.options.timeout_s,
                dry_run=req.options.dry_run,
            )

        # 简单启发式：检测 playwright/browser/e2e 关键字
        nl_lower = req.nl_input.lower()
        if "playwright" in nl_lower or "browser" in nl_lower or "e2e" in nl_lower:
            return OrchestrationInput(
                nl_input=req.nl_input,
                environment_id=req.environment_id,
                tool_name="run_playwright",
                tool_args={},
                timeout_s=300,
                dry_run=False,
            )

        # 默认：使用 'tests' 路径的 pytest
        return OrchestrationInput(
            nl_input=req.nl_input,
            environment_id=req.environment_id,
            tool_name="run_pytest",
            tool_args={"test_path": "tests"},
            timeout_s=120,
            dry_run=False,
        )

    def _load_policy(self, state: OrchestrationState) -> OrchestrationState:
        """节点 1：加载策略配置。

        使用注入的 policy_loader 或默认的 get_policy()。
        将 'policy' 和 'policy_meta' 添加到状态中。
        """
        policy = self._policy_loader()

        # 返回添加了策略的新状态（保留现有键）
        return {
            **state,
            "policy": policy,
            "policy_meta": {
                "version": policy.version,
                "high_risk_keywords_count": len(policy.high_risk_keywords),
                "high_risk_patterns_count": len(policy.high_risk_patterns),
            },
        }

    def _plan_tool_request(self, state: OrchestrationState) -> OrchestrationState:
        """节点 2：根据输入构建工具请求。

        从 OrchestrationInput 创建 ToolRequest。
        将 'tool_request' 添加到状态中。
        """
        input_data = state["input"]

        tool_request = ToolRequest(
            tool_name=input_data.tool_name,
            args=input_data.tool_args,
            run_id=state["run_id"],
            timeout_s=input_data.timeout_s,
            dry_run=input_data.dry_run,
        )

        return {
            **state,
            "tool_request": tool_request,
        }

    async def _execute_tools(self, state: OrchestrationState) -> OrchestrationState:
        """节点 3：执行工具并获取并汇总结果。

        使用注册表执行带有治理约束的工具请求。
        在状态中添加 'tool_result' 并更新 'budget'。
        """
        from datetime import datetime, timezone
        from qualityfoundry.tools.contracts import ToolStatus, ToolMetrics
        from qualityfoundry.tools.registry import ToolNotFoundError
        from qualityfoundry.tools.base import execute_with_governance

        tool_request = state["tool_request"]

        # 获取策略治理限制
        policy = state.get("policy")
        if policy and policy.cost_governance:
            # 将策略限制应用于请求
            tool_request = ToolRequest(
                tool_name=tool_request.tool_name,
                args=tool_request.args,
                run_id=tool_request.run_id,
                timeout_s=min(tool_request.timeout_s, policy.cost_governance.timeout_s),
                max_retries=policy.cost_governance.max_retries,
                dry_run=tool_request.dry_run,
                metadata=tool_request.metadata,
            )

        def tool_func(req: ToolRequest) -> ToolResult:
            return self.registry.execute(req.tool_name, req)

        try:
            # 在治理（超时 + 重试强制）约束下执行
            tool_result = await execute_with_governance(tool_func, tool_request)
        except ToolNotFoundError:
            now = datetime.now(timezone.utc)
            tool_result = ToolResult(
                status=ToolStatus.FAILED,
                stdout=None,
                stderr=f"未找到工具: {tool_request.tool_name}",
                error_message=f"未找到工具: {tool_request.tool_name}",
                started_at=now,
                ended_at=now,
                metrics=ToolMetrics(attempts=1, retries_used=0),
            )

        # 使用治理指标更新预算
        prev_budget = state.get("budget", {})
        new_budget: GovernanceBudget = {
            "elapsed_ms_total": prev_budget.get("elapsed_ms_total", 0) + tool_result.metrics.duration_ms,
            "attempts_total": prev_budget.get("attempts_total", 0) + tool_result.metrics.attempts,
            "retries_used_total": prev_budget.get("retries_used_total", 0) + tool_result.metrics.retries_used,
            "short_circuited": False,
            "short_circuit_reason": None,
        }

        return {
            **state,
            "tool_result": tool_result,
            "budget": new_budget,
        }

    def _collect_evidence(self, state: OrchestrationState) -> OrchestrationState:
        """节点 4：收集证据并保存到磁盘。

        使用 collector_factory 创建 TraceCollector。
        将 'evidence' 和 'report_path' 添加到状态中。
        在证据中包含治理预算信息 (Phase 5.1)。
        """
        run_id = state["run_id"]
        input_data = state["input"]
        tool_request = state["tool_request"]
        tool_result = state["tool_result"]
        budget = state.get("budget", {})
        policy = state.get("policy")

        # 使用环境信息创建收集器
        environment = {
            "environment_id": str(input_data.environment_id) if input_data.environment_id else None,
        }
        collector = self._collector_factory(run_id, input_data.nl_input, environment)

        # 添加工具结果
        collector.add_tool_result(tool_request.tool_name, tool_result)

        # 收集并保存证据
        evidence = collector.collect()

        # 将治理信息添加到证据字典中 (Phase 5.1)
        evidence_dict = evidence.model_dump()
        evidence_dict["governance"] = {
            "budget": {
                "elapsed_ms_total": budget.get("elapsed_ms_total", 0),
                "attempts_total": budget.get("attempts_total", 0),
                "retries_used_total": budget.get("retries_used_total", 0),
            },
            "policy_limits": {
                "timeout_s": policy.cost_governance.timeout_s if policy else None,
                "max_retries": policy.cost_governance.max_retries if policy else None,
            },
            "short_circuited": budget.get("short_circuited", False),
            "short_circuit_reason": budget.get("short_circuit_reason"),
            "decision_source": "governance_short_circuit" if budget.get("short_circuited") else "gate_evaluator",
        }

        report_path = collector.save(evidence)

        return {
            **state,
            "evidence": evidence_dict,
            "report_path": report_path,
        }

    def _gate_and_hitl(self, state: OrchestrationState) -> OrchestrationState:
        """节点 5：评估门禁并在需要时创建审批。

        使用 gate_evaluator 评估证据。
        将 'decision'、'reason' 和 'approval_id' 添加到状态中。
        """
        evidence_dict = state["evidence"]
        policy = state.get("policy")

        # 从字典重建 Evidence 对象以进行门禁评估
        evidence = Evidence.model_validate(evidence_dict)

        # 评估门禁
        gate_result = self._gate_evaluator(evidence, policy)

        # 如果需要人工审核 (NEED_HITL)，创建审批
        approval_id = None
        if gate_result.decision == GateDecision.NEED_HITL:
            try:
                approval = self._approval_service.create_approval(
                    entity_type="orchestration",
                    entity_id=state["run_id"],
                    reviewer=None,
                )
                approval_id = approval.id
            except Exception:
                # 审批创建失败不应阻塞主流程
                pass

        return {
            **state,
            "decision": gate_result.decision,
            "reason": gate_result.reason,
            "approval_id": approval_id,
        }

    def _enforce_budget(self, state: OrchestrationState) -> OrchestrationState:
        """节点 3.5：强制预算约束（如果超出则短路）。

        检查累计耗时是否超过策略超时。
        如果超出，则设置 short_circuit=True 并将决策设为 FAIL。
        """
        policy: PolicyConfig | None = state.get("policy")
        budget: GovernanceBudget = state.get("budget", {})
        elapsed_ms = budget.get("elapsed_ms_total", 0)

        # 从策略获取预算限制
        budget_ms = (policy.cost_governance.timeout_s * 1000) if policy else 300000  # 默认 5 分钟

        if elapsed_ms > budget_ms:
            return {
                **state,
                "budget": {
                    **budget,
                    "short_circuited": True,
                    "short_circuit_reason": "budget_elapsed_exceeded",
                },
                "decision": GateDecision.FAIL,
                "reason": f"超出预算: {elapsed_ms}ms > {budget_ms}ms (policy.cost_governance.timeout_s={budget_ms // 1000}s)",
            }

        return state


def build_orchestration_graph(service: OrchestratorService) -> CompiledStateGraph:
    """构建用于编排的 LangGraph 状态机。

    节点：
    1. load_policy: 加载策略配置
    2. plan_tool_request: 根据输入构建工具请求
    3. execute_tools: 执行工具并获取结果
    3.5. enforce_budget: 检查预算约束（可能导致短路）
    4. collect_evidence: 收集并保存证据
    5. gate_and_hitl: 评估门禁并在需要时创建审批

    条件路由：
    - enforce_budget 之后：如果已短路 (short_circuited) -> collect_evidence -> END (跳过门禁)
    - 否则：collect_evidence -> gate_and_hitl -> END

    参数：
        service: 注入了依赖项的 OrchestratorService 实例

    返回：
        编译好的可执行 StateGraph

    异常：
        ValueError: 如果 service 为 None
    """
    if service is None:
        raise ValueError("service 参数是必填的")

    def should_skip_gate(state: LangGraphState) -> str:
        """条件边：如果已短路，则跳过 gate_and_hitl。"""
        budget = state.get("budget", {})
        if budget.get("short_circuited"):
            return "end"
        return "gate_and_hitl"

    # 使用我们的状态类型创建图
    graph = StateGraph(LangGraphState)

    # 添加节点 - 包装服务方法
    graph.add_node("load_policy", service._load_policy)
    graph.add_node("plan_tool_request", service._plan_tool_request)
    graph.add_node("execute_tools", service._execute_tools)
    graph.add_node("enforce_budget", service._enforce_budget)
    graph.add_node("collect_evidence", service._collect_evidence)
    graph.add_node("gate_and_hitl", service._gate_and_hitl)

    # 定义带有短路条件路由的边
    graph.set_entry_point("load_policy")
    graph.add_edge("load_policy", "plan_tool_request")
    graph.add_edge("plan_tool_request", "execute_tools")
    graph.add_edge("execute_tools", "enforce_budget")
    graph.add_edge("enforce_budget", "collect_evidence")
    # collect_evidence 之后的条件边
    graph.add_conditional_edges(
        "collect_evidence",
        should_skip_gate,
        {
            "gate_and_hitl": "gate_and_hitl",
            "end": END,
        }
    )
    graph.add_edge("gate_and_hitl", END)

    # 编译并返回
    return graph.compile()
