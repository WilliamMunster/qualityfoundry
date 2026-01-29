"""Run 状态枚举定义

统一前后端状态认知，对外暴露精简状态集。
内部状态（LangGraph 节点）不直接暴露给客户端。
"""

from enum import Enum


class RunStatus(str, Enum):
    """Run 对外状态枚举
    
    状态流转:
        PENDING → RUNNING → [FINISHED|JUDGED]
                        ↓
                    FAILED (异常终止)
    
    说明:
        - PENDING: 已创建，等待执行
        - RUNNING: 正在执行（包含内部状态：PLANNED/EXECUTING/COLLECTING_EVIDENCE/DECIDING）
        - FINISHED: 执行完成但未经过门禁（异常情况）
        - JUDGED: 执行完成且已门禁决策（PASS/FAIL/NEED_HITL）
        - FAILED: 执行失败（异常终止，如沙箱错误、超时等）
    """
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"  # 完成但未决策（异常）
    JUDGED = "JUDGED"      # 完成并已决策
    FAILED = "FAILED"      # 异常失败
    
    @classmethod
    def terminal_states(cls) -> set[str]:
        """终态集合"""
        return {cls.FINISHED.value, cls.JUDGED.value, cls.FAILED.value}
    
    @classmethod
    def active_states(cls) -> set[str]:
        """进行中状态集合"""
        return {cls.PENDING.value, cls.RUNNING.value}
    
    def is_terminal(self) -> bool:
        """是否为终态"""
        return self.value in self.terminal_states()


class RunDecision(str, Enum):
    """Run 决策结果枚举"""
    PASS = "PASS"
    FAIL = "FAIL"
    NEED_HITL = "NEED_HITL"


def map_internal_status_to_external(
    has_tool_started: bool,
    has_tool_finished: bool,
    has_decision: bool,
    has_error: bool = False,
) -> RunStatus:
    """将内部审计事件映射为对外状态
    
    简化策略：
        - 无事件 -> PENDING
        - 有 TOOL_STARTED 无 TOOL_FINISHED -> RUNNING
        - 有 TOOL_FINISHED 无 DECISION -> FINISHED (异常)
        - 有 DECISION -> JUDGED
        - 有 ERROR -> FAILED
    
    Args:
        has_tool_started: 是否有工具启动事件
        has_tool_finished: 是否有工具完成事件
        has_decision: 是否有决策事件
        has_error: 是否有错误事件
        
    Returns:
        RunStatus 对外状态
    """
    if has_error:
        return RunStatus.FAILED
    
    if has_decision:
        return RunStatus.JUDGED
    
    if has_tool_finished:
        # 执行完成但没有决策（异常情况）
        return RunStatus.FINISHED
    
    if has_tool_started:
        return RunStatus.RUNNING
    
    return RunStatus.PENDING


__all__ = [
    "RunStatus",
    "RunDecision",
    "map_internal_status_to_external",
]
