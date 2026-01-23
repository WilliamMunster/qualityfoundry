"""Audit Context for MCP Server

每次 tool 调用的审计元数据提取与哈希生成。
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from qualityfoundry.governance.repro import get_git_sha
from qualityfoundry.governance.policy_loader import get_policy

logger = logging.getLogger(__name__)


@dataclass
class AuditContext:
    """审计上下文元数据"""

    request_id: UUID = field(default_factory=uuid4)
    actor: str | None = None
    policy_hash: str | None = None
    git_sha: str | None = None
    args_hash: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            "request_id": str(self.request_id),
            "actor": self.actor,
            "policy_hash": self.policy_hash,
            "git_sha": self.git_sha,
            "args_hash": self.args_hash,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


def _hash_args(args: dict[str, Any]) -> str:
    """计算参数的 SHA256 哈希"""
    canonical = json.dumps(args, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _hash_policy(policy_dict: dict[str, Any]) -> str:
    """计算策略配置的 SHA256 哈希"""
    canonical = json.dumps(policy_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def get_audit_context(
    args: dict[str, Any] | None = None,
    actor: str | None = None,
) -> AuditContext:
    """
    获取当前调用的审计上下文。

    Args:
        args: 工具调用参数
        actor: 调用者标识（可选）

    Returns:
        填充了元数据的 AuditContext
    """
    policy = get_policy()
    policy_hash = _hash_policy(policy.model_dump())
    git_sha = get_git_sha()
    args_hash = _hash_args(args) if args else None

    ctx = AuditContext(
        actor=actor,
        policy_hash=policy_hash,
        git_sha=git_sha,
        args_hash=args_hash,
    )

    logger.info(f"AuditContext created: {ctx.to_json()}")
    return ctx
