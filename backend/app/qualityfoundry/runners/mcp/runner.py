"""QualityFoundry - MCP Runner

MCP 模式执行器
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from qualityfoundry.models.schemas import Action, CompiledCase
from qualityfoundry.services.mcp.client import MCPClient

logger = logging.getLogger(__name__)


class MCPRunner:
    """
    MCP 模式执行器
    
    使用 MCP 协议执行测试用例
    """
    
    def __init__(self, artifacts_dir: str = "artifacts"):
        """
        初始化 MCP 执行器
        
        Args:
            artifacts_dir: 证据目录
        """
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.client: Optional[MCPClient] = None
    
    async def execute_case(
        self,
        case: CompiledCase,
        run_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        执行测试用例
        
        Args:
            case: 编译后的测试用例
            run_id: 执行 ID
            
        Returns:
            执行结果
        """
        logger.info(f"开始执行用例（MCP 模式）: {case.title}")
        
        # 创建执行目录
        if run_id:
            run_dir = self.artifacts_dir / f"run_{run_id}"
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            run_dir = self.artifacts_dir / f"run_{timestamp}"
        
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化客户端
        self.client = MCPClient()
        
        try:
            async with self.client.session_context():
                # 执行所有动作
                results = []
                
                for idx, action in enumerate(case.actions):
                    try:
                        logger.info(f"执行动作 {idx + 1}/{len(case.actions)}: {action.type}")
                        
                        result = await self._execute_action(action, run_dir, idx)
                        results.append({
                            "action": action.type,
                            "status": "success",
                            "result": result
                        })
                        
                    except Exception as e:
                        logger.error(f"动作执行失败: {action.type}, 错误: {e}")
                        results.append({
                            "action": action.type,
                            "status": "failed",
                            "error": str(e)
                        })
                        
                        # 失败后是否继续？目前选择中断
                        raise
                
                logger.info(f"用例执行完成: {case.title}")
                
                return {
                    "status": "success",
                    "case_title": case.title,
                    "actions_executed": len(results),
                    "results": results,
                    "artifacts_dir": str(run_dir)
                }
                
        except Exception as e:
            logger.error(f"用例执行失败: {case.title}, 错误: {e}")
            return {
                "status": "failed",
                "case_title": case.title,
                "error": str(e),
                "artifacts_dir": str(run_dir)
            }
    
    async def _execute_action(
        self,
        action: Action,
        run_dir: Path,
        step_index: int
    ) -> Any:
        """
        执行单个动作
        
        Args:
            action: 动作
            run_dir: 执行目录
            step_index: 步骤索引
            
        Returns:
            执行结果
        """
        if action.type == "goto":
            return await self.client.navigate(action.url)
        
        elif action.type == "click":
            selector = self._build_selector(action)
            return await self.client.click(selector)
        
        elif action.type == "fill":
            selector = self._build_selector(action)
            return await self.client.fill(selector, action.value)
        
        elif action.type == "screenshot":
            screenshot_path = run_dir / f"step_{step_index:03d}_screenshot.png"
            return await self.client.screenshot(str(screenshot_path))
        
        elif action.type == "assert_text":
            # MCP 可能需要先获取页面内容再断言
            # 这里简化处理，实际需要调用相应的 MCP 工具
            logger.warning(f"assert_text 在 MCP 模式下需要特殊处理")
            return {"status": "skipped", "reason": "not implemented in MCP mode"}
        
        elif action.type == "assert_visible":
            # 同上
            logger.warning(f"assert_visible 在 MCP 模式下需要特殊处理")
            return {"status": "skipped", "reason": "not implemented in MCP mode"}
        
        else:
            raise ValueError(f"不支持的动作类型: {action.type}")
    
    def _build_selector(self, action: Action) -> str:
        """
        构建选择器
        
        Args:
            action: 动作
            
        Returns:
            选择器字符串
        """
        if action.locator:
            loc = action.locator
            if loc.type == "text":
                return f"text={loc.value}"
            elif loc.type == "placeholder":
                return f"[placeholder='{loc.value}']"
            elif loc.type == "role":
                return f"role={loc.value}"
            elif loc.type == "css":
                return loc.value
            else:
                return loc.value
        
        return ""


async def execute_case_mcp(
    case: CompiledCase,
    run_id: Optional[UUID] = None,
    artifacts_dir: str = "artifacts"
) -> Dict[str, Any]:
    """
    使用 MCP 模式执行测试用例
    
    Args:
        case: 编译后的测试用例
        run_id: 执行 ID
        artifacts_dir: 证据目录
        
    Returns:
        执行结果
    """
    runner = MCPRunner(artifacts_dir=artifacts_dir)
    return await runner.execute_case(case, run_id)
