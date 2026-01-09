"""QualityFoundry - MCP Client

生产级 MCP 客户端实现
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP 客户端
    
    提供与 Playwright MCP Server 的连接和工具调用能力
    """
    
    def __init__(
        self,
        server_command: str = "npx",
        server_args: Optional[List[str]] = None
    ):
        """
        初始化 MCP 客户端
        
        Args:
            server_command: MCP 服务器启动命令
            server_args: 服务器参数
        """
        self.server_command = server_command
        self.server_args = server_args or ["-y", "@modelcontextprotocol/server-playwright"]
        self.session: Optional[ClientSession] = None
        self._read = None
        self._write = None
        self._client_context = None
        
    async def connect(self):
        """连接到 MCP 服务器"""
        try:
            logger.info(f"连接到 MCP 服务器: {self.server_command} {' '.join(self.server_args)}")
            
            server_params = StdioServerParameters(
                command=self.server_command,
                args=self.server_args
            )
            
            # 创建客户端连接
            self._client_context = stdio_client(server_params)
            self._read, self._write = await self._client_context.__aenter__()
            
            # 创建会话
            self.session = ClientSession(self._read, self._write)
            await self.session.__aenter__()
            
            # 初始化
            await self.session.initialize()
            
            logger.info("MCP 客户端连接成功")
            
        except Exception as e:
            logger.error(f"MCP 客户端连接失败: {e}")
            raise
    
    async def disconnect(self):
        """断开 MCP 服务器连接"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            
            if self._client_context:
                await self._client_context.__aexit__(None, None, None)
            
            logger.info("MCP 客户端已断开")
            
        except Exception as e:
            logger.error(f"MCP 客户端断开失败: {e}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出可用工具
        
        Returns:
            工具列表
        """
        if not self.session:
            raise RuntimeError("MCP 客户端未连接")
        
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            logger.error(f"列出工具失败: {e}")
            raise
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        max_retries: int = 3
    ) -> Any:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            max_retries: 最大重试次数
            
        Returns:
            工具调用结果
        """
        if not self.session:
            raise RuntimeError("MCP 客户端未连接")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"调用工具: {tool_name}, 参数: {arguments}")
                
                result = await self.session.call_tool(
                    name=tool_name,
                    arguments=arguments
                )
                
                logger.info(f"工具调用成功: {tool_name}")
                return result
                
            except Exception as e:
                logger.warning(f"工具调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt == max_retries - 1:
                    logger.error(f"工具调用最终失败: {tool_name}")
                    raise
                
                # 等待后重试
                await asyncio.sleep(1 * (attempt + 1))
    
    async def navigate(self, url: str) -> Any:
        """
        导航到 URL
        
        Args:
            url: 目标 URL
            
        Returns:
            导航结果
        """
        return await self.call_tool("playwright_navigate", {"url": url})
    
    async def click(self, selector: str) -> Any:
        """
        点击元素
        
        Args:
            selector: 元素选择器
            
        Returns:
            点击结果
        """
        return await self.call_tool("playwright_click", {"selector": selector})
    
    async def fill(self, selector: str, value: str) -> Any:
        """
        填充输入框
        
        Args:
            selector: 元素选择器
            value: 填充值
            
        Returns:
            填充结果
        """
        return await self.call_tool("playwright_fill", {
            "selector": selector,
            "value": value
        })
    
    async def screenshot(self, path: str) -> Any:
        """
        截图
        
        Args:
            path: 截图保存路径
            
        Returns:
            截图结果
        """
        return await self.call_tool("playwright_screenshot", {"path": path})
    
    @asynccontextmanager
    async def session_context(self):
        """
        会话上下文管理器
        
        用法:
            async with client.session_context():
                await client.navigate("https://example.com")
        """
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()


# 全局客户端实例（单例模式）
_mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """
    获取全局 MCP 客户端实例
    
    Returns:
        MCP 客户端
    """
    global _mcp_client
    
    if _mcp_client is None:
        _mcp_client = MCPClient()
        await _mcp_client.connect()
    
    return _mcp_client


async def close_mcp_client():
    """关闭全局 MCP 客户端"""
    global _mcp_client
    
    if _mcp_client:
        await _mcp_client.disconnect()
        _mcp_client = None
