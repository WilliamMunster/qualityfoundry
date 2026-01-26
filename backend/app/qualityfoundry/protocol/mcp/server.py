"""QualityFoundry MCP Server

MCP Server 实现，支持只读工具和受安全链约束的写工具。

Phase 1: 仅 run_pytest 作为写工具，必须满足：
- 认证（params.auth.token）
- 权限（ORCHESTRATION_RUN）
- 策略（allowlist 非空 + 工具在 allowlist）
- 沙箱（sandbox.enabled=true）
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
import time
from typing import Any
from uuid import uuid4

from qualityfoundry.protocol.mcp.audit_context import get_audit_context
from qualityfoundry.protocol.mcp.tools import (
    SAFE_TOOLS,
    READ_HANDLERS,
    WRITE_HANDLERS,
    is_write_tool,
)
from qualityfoundry.protocol.mcp.errors import (
    AUTH_REQUIRED,
    PERMISSION_DENIED,
    POLICY_BLOCKED,
    SANDBOX_VIOLATION,
    TIMEOUT,
    RATE_LIMITED,
    QUOTA_EXCEEDED,
    make_error_response,
)
from qualityfoundry.protocol.mcp.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server 实现（JSON-RPC over stdio）

    安全链路（仅对写工具）：
    1. 认证：params.auth.token → AuthService.verify_token() → User
    2. 权限：User.role 必须具备 ORCHESTRATION_RUN
    3. 策略：policy.tools.allowlist 必须非空且包含工具
    4. 沙箱：policy.sandbox.enabled 必须为 true
    """

    def __init__(self, db_session_factory=None):
        """初始化 MCP Server

        Args:
            db_session_factory: 数据库会话工厂（用于认证）
        """
        self._running = False
        self._db_session_factory = db_session_factory

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

    def _verify_auth(self, params: dict[str, Any]) -> tuple[Any | None, dict | None]:
        """验证认证

        Args:
            params: JSON-RPC params

        Returns:
            (user, error_response) - user 为 None 时 error_response 有值
        """
        auth = params.get("auth", {})
        token = auth.get("token")

        if not token:
            return None, {"code": AUTH_REQUIRED, "message": "Authentication required"}

        if self._db_session_factory is None:
            logger.warning("No db_session_factory configured, auth will fail")
            return None, {"code": AUTH_REQUIRED, "message": "Authentication not configured"}

        from qualityfoundry.services.auth_service import AuthService

        with self._db_session_factory() as db:
            user = AuthService.verify_token(db, token)
            if user is None:
                return None, {"code": AUTH_REQUIRED, "message": "Invalid or expired token"}
            return user, None

    def _check_permission(self, user: Any, tool_name: str) -> dict | None:
        """检查用户权限

        Args:
            user: User 对象
            tool_name: 工具名

        Returns:
            错误对象（如果有），否则 None
        """
        from qualityfoundry.database.user_models import UserRole

        # 写工具需要 USER 或 ADMIN 角色
        if is_write_tool(tool_name):
            if user.role == UserRole.VIEWER:
                return {"code": PERMISSION_DENIED, "message": "Permission denied: VIEWER cannot run write tools"}
        return None

    def _check_policy(self, tool_name: str) -> tuple[Any | None, dict | None]:
        """检查策略

        Args:
            tool_name: 工具名

        Returns:
            (policy, error) - policy 为 None 时 error 有值
        """
        from qualityfoundry.governance.policy_loader import get_policy

        policy = get_policy()

        # MCP 写模式：allowlist 必须非空
        if is_write_tool(tool_name):
            if not policy.tools.allowlist:
                return None, {
                    "code": POLICY_BLOCKED,
                    "message": "MCP write requires explicit allowlist",
                }
            if tool_name not in policy.tools.allowlist:
                return None, {
                    "code": POLICY_BLOCKED,
                    "message": f"Tool '{tool_name}' not in policy allowlist",
                }

        return policy, None

    def _check_sandbox(self, policy: Any, tool_name: str) -> dict | None:
        """检查沙箱配置

        Args:
            policy: PolicyConfig
            tool_name: 工具名

        Returns:
            错误对象（如果有），否则 None
        """
        if is_write_tool(tool_name):
            if not policy.sandbox.enabled:
                return {
                    "code": SANDBOX_VIOLATION,
                    "message": "MCP write requires sandbox.enabled=true",
                }
        return None

    def _check_rate_limit(self, user_id: str) -> dict | None:
        """检查速率限制

        Args:
            user_id: 用户 ID

        Returns:
            错误对象（如果有），否则 None
        """
        result = get_rate_limiter().check_limits(str(user_id))
        if not result.allowed:
            if result.reason == "QUOTA_EXCEEDED":
                return {
                    "code": QUOTA_EXCEEDED,
                    "message": "Daily quota exceeded",
                    "data": {"reason": result.reason},
                }
            else:
                return {
                    "code": RATE_LIMITED,
                    "message": f"Rate limited: {result.reason}",
                    "data": {
                        "reason": result.reason,
                        "retry_after_seconds": result.retry_after_seconds,
                    },
                }
        return None

    def _write_audit_log(
        self,
        run_id,
        tool_name: str,
        user_id=None,
        args_hash: str | None = None,
        status: str = "started",
        details: dict | None = None,
    ):
        """写入审计日志（MCP_TOOL_CALL 事件）"""
        if self._db_session_factory is None:
            logger.warning("No db_session_factory, skipping audit log")
            return

        try:
            from qualityfoundry.database.audit_log_models import AuditLog, AuditEventType

            with self._db_session_factory() as db:
                log = AuditLog(
                    run_id=run_id,
                    created_by_user_id=user_id,
                    event_type=AuditEventType.MCP_TOOL_CALL,
                    tool_name=tool_name,
                    args_hash=args_hash,
                    status=status,
                    details=json.dumps(details) if details else None,
                )
                db.add(log)
                db.commit()
        except Exception as e:
            # 审计写入失败不阻断主流程
            logger.exception(f"Failed to write audit log: {e}")

    async def handle_tool_call(
        self, tool_name: str, arguments: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any]:
        """处理工具调用

        安全链路：
        1. 生成 run_id
        2. 如果是写工具：auth → permission → policy → sandbox
        3. 执行工具
        4. 写入审计
        """
        run_id = uuid4()
        audit_ctx = get_audit_context(args=arguments)
        args_hash = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()[:16]

        logger.info(f"Tool call: {tool_name}, run_id={run_id}, audit={audit_ctx.to_json()}")

        user = None
        policy = None

        # ==================== 写工具安全链 ====================
        if is_write_tool(tool_name):
            # 1. 认证
            user, auth_error = self._verify_auth(params)
            if auth_error:
                self._write_audit_log(run_id, tool_name, args_hash=args_hash, status="auth_failed")
                return {"error": auth_error}

            # 2. 权限
            perm_error = self._check_permission(user, tool_name)
            if perm_error:
                self._write_audit_log(
                    run_id, tool_name, user_id=user.id, args_hash=args_hash, status="permission_denied"
                )
                return {"error": perm_error}

            # 3. 速率限制 (新增)
            rate_error = self._check_rate_limit(user.id)
            if rate_error:
                self._write_audit_log(
                    run_id, tool_name, user_id=user.id, args_hash=args_hash,
                    status="rate_limited" if rate_error["code"] == RATE_LIMITED else "quota_exceeded",
                    details={"reason": rate_error.get("data", {}).get("reason")},
                )
                return {"error": rate_error}

            # 4. 策略
            policy, policy_error = self._check_policy(tool_name)
            if policy_error:
                self._write_audit_log(
                    run_id, tool_name, user_id=user.id, args_hash=args_hash, status="policy_blocked"
                )
                return {"error": policy_error}

            # 5. 沙箱
            sandbox_error = self._check_sandbox(policy, tool_name)
            if sandbox_error:
                self._write_audit_log(
                    run_id, tool_name, user_id=user.id, args_hash=args_hash, status="sandbox_violation"
                )
                return {"error": sandbox_error}

            # 获取执行槽位
            get_rate_limiter().acquire(str(user.id))

            # 写入入口审计
            self._write_audit_log(
                run_id, tool_name, user_id=user.id, args_hash=args_hash, status="started"
            )

        # ==================== 执行工具 ====================
        if tool_name in READ_HANDLERS:
            handler = READ_HANDLERS[tool_name]
            try:
                result = await handler(**arguments)
                result["audit_context"] = audit_ctx.to_dict()
                return result
            except Exception as e:
                logger.exception(f"Tool {tool_name} failed")
                return {"error": str(e), "audit_context": audit_ctx.to_dict()}

        elif tool_name in WRITE_HANDLERS:
            handler = WRITE_HANDLERS[tool_name]
            start_time = time.monotonic()
            try:
                # 写工具传递额外参数
                result = await handler(
                    **arguments,
                    run_id=run_id,
                    policy=policy,
                )
                result["audit_context"] = audit_ctx.to_dict()

                # 写入完成审计
                elapsed_ms = (time.monotonic() - start_time) * 1000
                self._write_audit_log(
                    run_id,
                    tool_name,
                    user_id=user.id if user else None,
                    args_hash=args_hash,
                    status=result.get("status", "completed"),
                    details={"elapsed_ms": elapsed_ms},
                )
                return result
            except asyncio.TimeoutError:
                self._write_audit_log(
                    run_id,
                    tool_name,
                    user_id=user.id if user else None,
                    args_hash=args_hash,
                    status="timeout",
                )
                return {"error": {"code": TIMEOUT, "message": "Execution timeout"}}
            except Exception as e:
                logger.exception(f"Tool {tool_name} failed")
                self._write_audit_log(
                    run_id,
                    tool_name,
                    user_id=user.id if user else None,
                    args_hash=args_hash,
                    status="failed",
                    details={"error": str(e)},
                )
                return {"error": str(e), "audit_context": audit_ctx.to_dict()}
            finally:
                # 释放执行槽位
                if user:
                    elapsed_ms = (time.monotonic() - start_time) * 1000
                    get_rate_limiter().release(str(user.id), elapsed_ms)

        else:
            return {"error": f"Unknown tool: {tool_name}", "audit_context": audit_ctx.to_dict()}

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
                        "version": "0.2.0",  # Bumped for write capability
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
            result = await self.handle_tool_call(tool_name, arguments, params)

            # 检查是否有结构化错误
            if "error" in result and isinstance(result["error"], dict):
                return make_error_response(req_id, result["error"]["code"], result["error"]["message"])

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


def create_server(db_session_factory=None) -> MCPServer:
    """创建 MCP Server 实例

    Args:
        db_session_factory: 数据库会话工厂（用于认证和审计）
    """
    return MCPServer(db_session_factory=db_session_factory)


async def main():
    """Server 入口"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # 日志输出到 stderr，stdout 用于协议
    )

    # 创建数据库会话工厂
    from qualityfoundry.database.config import SessionLocal

    def db_factory():
        return SessionLocal()

    server = create_server(db_session_factory=db_factory)
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
