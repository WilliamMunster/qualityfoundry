"""MCP Server Error Codes

JSON-RPC 2.0 错误码定义，用于 MCP write capability 安全边界。
"""

from __future__ import annotations

from typing import Any


# ==================== MCP 自定义错误码 ====================
# 基于 JSON-RPC 2.0 规范：-32000 to -32099 为服务器定义错误

AUTH_REQUIRED = -32001
PERMISSION_DENIED = -32003
POLICY_BLOCKED = -32004
BUDGET_EXCEEDED = -32005
SANDBOX_VIOLATION = -32006
TIMEOUT = -32007
RATE_LIMITED = -32008       # 速率/并发限制
QUOTA_EXCEEDED = -32009     # 配额超限

# JSON-RPC 标准错误码
INVALID_PARAMS = -32602
METHOD_NOT_FOUND = -32601


# ==================== 错误消息模板 ====================

ERROR_MESSAGES = {
    AUTH_REQUIRED: "Authentication required",
    PERMISSION_DENIED: "Permission denied",
    POLICY_BLOCKED: "Tool blocked by policy",
    BUDGET_EXCEEDED: "Budget exceeded",
    SANDBOX_VIOLATION: "Sandbox violation",
    TIMEOUT: "Execution timeout",
    RATE_LIMITED: "Rate limited",
    QUOTA_EXCEEDED: "Quota exceeded",
    INVALID_PARAMS: "Invalid params",
    METHOD_NOT_FOUND: "Method not found",
}


def make_error(
    code: int,
    message: str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构建 JSON-RPC 2.0 错误对象

    Args:
        code: 错误码（如 AUTH_REQUIRED）
        message: 错误消息（可选，默认从 ERROR_MESSAGES 获取）
        data: 附加数据（可选）

    Returns:
        符合 JSON-RPC 2.0 的错误对象
    """
    error: dict[str, Any] = {
        "code": code,
        "message": message or ERROR_MESSAGES.get(code, "Unknown error"),
    }
    if data is not None:
        error["data"] = data
    return error


def make_error_response(
    req_id: int | str | None,
    code: int,
    message: str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构建完整的 JSON-RPC 2.0 错误响应

    Args:
        req_id: 请求 ID
        code: 错误码
        message: 错误消息
        data: 附加数据

    Returns:
        完整的 JSON-RPC 2.0 错误响应
    """
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": make_error(code, message, data),
    }
