"""QualityFoundry - Execution Mode Manager

执行模式管理器
"""
import asyncio
import logging
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from qualityfoundry.models.schemas import CompiledCase
from qualityfoundry.runners.playwright.runner import execute_case as execute_case_dsl
from qualityfoundry.runners.mcp.runner import execute_case_mcp

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """执行模式"""
    DSL = "dsl"  # 使用现有 DSL 执行器
    MCP = "mcp"  # 使用 MCP 执行器
    HYBRID = "hybrid"  # 智能选择


class ExecutionModeManager:
    """
    执行模式管理器
    
    统一的执行入口，支持多种执行模式
    """
    
    def __init__(self, default_mode: ExecutionMode = ExecutionMode.HYBRID):
        """
        初始化执行模式管理器
        
        Args:
            default_mode: 默认执行模式
        """
        self.default_mode = default_mode
    
    async def execute(
        self,
        case: CompiledCase,
        mode: Optional[ExecutionMode] = None,
        run_id: Optional[UUID] = None,
        artifacts_dir: str = "artifacts"
    ) -> Dict[str, Any]:
        """
        执行测试用例
        
        Args:
            case: 编译后的测试用例
            mode: 执行模式（None 则使用默认模式）
            run_id: 执行 ID
            artifacts_dir: 证据目录
            
        Returns:
            执行结果
        """
        # 确定执行模式
        execution_mode = mode or self.default_mode
        
        # Hybrid 模式：智能选择
        if execution_mode == ExecutionMode.HYBRID:
            execution_mode = self._select_mode(case)
            logger.info(f"Hybrid 模式选择: {execution_mode}")
        
        # 根据模式执行
        if execution_mode == ExecutionMode.DSL:
            return await self._execute_dsl(case, run_id, artifacts_dir)
        elif execution_mode == ExecutionMode.MCP:
            return await self._execute_mcp(case, run_id, artifacts_dir)
        else:
            raise ValueError(f"不支持的执行模式: {execution_mode}")
    
    def _select_mode(self, case: CompiledCase) -> ExecutionMode:
        """
        智能选择执行模式
        
        Args:
            case: 测试用例
            
        Returns:
            选择的执行模式
        """
        # 简单的启发式规则：
        # 1. 如果动作数量 <= 5，使用 DSL（简单场景）
        # 2. 如果包含复杂断言，使用 DSL
        # 3. 否则使用 MCP
        
        action_count = len(case.actions)
        
        # 检查是否有复杂断言
        has_complex_assertion = any(
            action.type in ["assert_text", "assert_visible"]
            for action in case.actions
        )
        
        if action_count <= 5 or has_complex_assertion:
            return ExecutionMode.DSL
        else:
            return ExecutionMode.MCP
    
    async def _execute_dsl(
        self,
        case: CompiledCase,
        run_id: Optional[UUID],
        artifacts_dir: str
    ) -> Dict[str, Any]:
        """
        使用 DSL 模式执行
        
        Args:
            case: 测试用例
            run_id: 执行 ID
            artifacts_dir: 证据目录
            
        Returns:
            执行结果
        """
        logger.info(f"使用 DSL 模式执行: {case.title}")
        
        try:
            # DSL 执行器是同步的，需要在线程池中运行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                execute_case_dsl,
                case,
                artifacts_dir
            )
            
            return {
                "mode": "dsl",
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"DSL 模式执行失败: {e}")
            return {
                "mode": "dsl",
                "status": "failed",
                "error": str(e)
            }
    
    async def _execute_mcp(
        self,
        case: CompiledCase,
        run_id: Optional[UUID],
        artifacts_dir: str
    ) -> Dict[str, Any]:
        """
        使用 MCP 模式执行
        
        Args:
            case: 测试用例
            run_id: 执行 ID
            artifacts_dir: 证据目录
            
        Returns:
            执行结果
        """
        logger.info(f"使用 MCP 模式执行: {case.title}")
        
        try:
            result = await execute_case_mcp(case, run_id, artifacts_dir)
            
            return {
                "mode": "mcp",
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"MCP 模式执行失败: {e}")
            return {
                "mode": "mcp",
                "status": "failed",
                "error": str(e)
            }


# 全局执行模式管理器
_execution_manager: Optional[ExecutionModeManager] = None


def get_execution_manager() -> ExecutionModeManager:
    """
    获取全局执行模式管理器
    
    Returns:
        执行模式管理器
    """
    global _execution_manager
    
    if _execution_manager is None:
        _execution_manager = ExecutionModeManager()
    
    return _execution_manager


async def execute_case_with_mode(
    case: CompiledCase,
    mode: Optional[ExecutionMode] = None,
    run_id: Optional[UUID] = None,
    artifacts_dir: str = "artifacts"
) -> Dict[str, Any]:
    """
    使用指定模式执行测试用例
    
    Args:
        case: 编译后的测试用例
        mode: 执行模式
        run_id: 执行 ID
        artifacts_dir: 证据目录
        
    Returns:
        执行结果
    """
    manager = get_execution_manager()
    return await manager.execute(case, mode, run_id, artifacts_dir)
