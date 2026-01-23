"""QualityFoundry MCP Server

最小 MCP Server 实现，暴露只读安全工具。
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from qualityfoundry.protocol.mcp.audit_context import get_audit_context
from qualityfoundry.protocol.mcp.tools import SAFE_TOOLS, TOOL_HANDLERS

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server 实现（JSON-RPC over stdio）"""

    def __init__(self):
        self._running = False

    def get_tool_list(self) -> list[dict[str, Any]]:
        """返回可用工具列表"""
        return [
            {
                "name": name,
                "description": info["description"],
                "inputSchema": info["parameters"],
            }
            for name, info in SAFE_TOOLS.items()
        ]

    async def handle_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """处理工具调用"""
        # 生成审计上下文
        audit_ctx = get_audit_context(args=arguments)
        logger.info(f"Tool call: {tool_name}, audit={audit_ctx.to_json()}")

        if tool_name not in TOOL_HANDLERS:
            return {
                "error": f"Unknown tool: {tool_name}",
                "audit_context": audit_ctx.to_dict(),
            }

        handler = TOOL_HANDLERS[tool_name]
        try:
            result = await handler(**arguments)
            result["audit_context"] = audit_ctx.to_dict()
            return result
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed")
            return {
                "error": str(e),
                "audit_context": audit_ctx.to_dict(),
            }

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理 JSON-RPC 请求"""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "qualityfoundry-mcp",
                        "version": "0.1.0",
                    },
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.get_tool_list()},
            }

        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = await self.handle_tool_call(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": "error" in result,
                },
            }

        # 未知方法
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    async def run_stdio(self):
        """运行 stdio 模式的 MCP Server"""
        self._running = True
        logger.info("MCP Server starting (stdio mode)")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

        while self._running:
            try:
                line = await reader.readline()
                if not line:
                    break

                request = json.loads(line.decode())
                response = await self.handle_request(request)
                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
            except Exception as e:
                logger.exception(f"Error processing request: {e}")

        logger.info("MCP Server stopped")

    def stop(self):
        """停止服务器"""
        self._running = False


def create_server() -> MCPServer:
    """创建 MCP Server 实例"""
    return MCPServer()


async def main():
    """Server 入口"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # 日志输出到 stderr，stdout 用于协议
    )
    server = create_server()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
