"""Smoke Tests for MCP Server (PR-A)

验证 MCP Server 的基本功能。
"""

import json
from uuid import uuid4

import pytest

from qualityfoundry.protocol.mcp.server import MCPServer, create_server
from qualityfoundry.protocol.mcp.audit_context import get_audit_context, AuditContext
from qualityfoundry.protocol.mcp.tools import get_evidence, list_artifacts


class TestMCPServerBasics:
    """MCP Server 基础测试"""

    def test_create_server(self):
        """可以创建 server 实例"""
        server = create_server()
        assert isinstance(server, MCPServer)

    def test_tool_list(self):
        """工具列表包含预期工具"""
        server = MCPServer()
        tools = server.get_tool_list()

        assert len(tools) == 3
        names = {t["name"] for t in tools}
        assert "get_evidence" in names
        assert "list_artifacts" in names
        assert "get_artifact_content" in names

    def test_tool_list_has_schema(self):
        """工具定义包含输入 schema"""
        server = MCPServer()
        tools = server.get_tool_list()

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"


class TestMCPProtocol:
    """MCP 协议处理测试"""

    @pytest.mark.asyncio
    async def test_initialize_request(self):
        """处理 initialize 请求"""
        server = MCPServer()
        response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "qualityfoundry-mcp"

    @pytest.mark.asyncio
    async def test_tools_list_request(self):
        """处理 tools/list 请求"""
        server = MCPServer()
        response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })

        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 3

    @pytest.mark.asyncio
    async def test_unknown_method(self):
        """未知方法返回错误"""
        server = MCPServer()
        response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "unknown/method",
            "params": {},
        })

        assert response["id"] == 3
        assert "error" in response
        assert response["error"]["code"] == -32601


class TestToolHandlers:
    """工具处理器测试"""

    @pytest.mark.asyncio
    async def test_get_evidence_not_found(self):
        """evidence 不存在时返回错误"""
        result = await get_evidence(str(uuid4()))
        assert "error" in result
        assert result["error"] == "Evidence not found"

    @pytest.mark.asyncio
    async def test_get_evidence_invalid_uuid(self):
        """无效 UUID 返回错误"""
        result = await get_evidence("not-a-uuid")
        assert "error" in result
        assert "Invalid run_id" in result["error"]

    @pytest.mark.asyncio
    async def test_list_artifacts_not_found(self):
        """运行目录不存在时返回错误"""
        result = await list_artifacts(str(uuid4()))
        assert "error" in result
        assert "not found" in result["error"]


class TestAuditContext:
    """审计上下文测试"""

    def test_audit_context_creation(self):
        """可以创建审计上下文"""
        ctx = get_audit_context(args={"run_id": "test"})

        assert isinstance(ctx, AuditContext)
        assert ctx.request_id is not None
        assert ctx.args_hash is not None
        assert ctx.timestamp is not None

    def test_audit_context_to_dict(self):
        """可以序列化为字典"""
        ctx = get_audit_context(args={"foo": "bar"}, actor="test-user")
        d = ctx.to_dict()

        assert "request_id" in d
        assert "actor" in d
        assert d["actor"] == "test-user"
        assert "policy_hash" in d
        assert "args_hash" in d
        assert "timestamp" in d

    def test_audit_context_to_json(self):
        """可以序列化为 JSON"""
        ctx = get_audit_context()
        j = ctx.to_json()

        parsed = json.loads(j)
        assert "request_id" in parsed


class TestToolCallWithAudit:
    """工具调用审计测试"""

    @pytest.mark.asyncio
    async def test_tool_call_includes_audit(self):
        """工具调用结果包含审计上下文"""
        server = MCPServer()
        result = await server.handle_tool_call(
            "get_evidence",
            {"run_id": str(uuid4())}
        )

        assert "audit_context" in result
        assert "request_id" in result["audit_context"]
        assert "policy_hash" in result["audit_context"]

    @pytest.mark.asyncio
    async def test_unknown_tool_includes_audit(self):
        """未知工具调用也包含审计上下文"""
        server = MCPServer()
        result = await server.handle_tool_call(
            "unknown_tool",
            {}
        )

        assert "error" in result
        assert "audit_context" in result
