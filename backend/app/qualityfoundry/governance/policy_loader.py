"""QualityFoundry - Policy Loader (L1 Policy Layer)

加载和验证策略配置文件 (policy_config.yaml)。

Features:
- Pydantic schema 验证
- YAML 加载
- 默认值回退
- 环境变量路径覆盖
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 默认策略文件路径（相对于此模块）
DEFAULT_POLICY_PATH = Path(__file__).parent / "policy_config.yaml"

# 环境变量覆盖
ENV_POLICY_PATH = "QF_POLICY_PATH"


class JUnitPassRule(BaseModel):
    """JUnit 通过规则"""
    max_failures: int = Field(default=0, ge=0, description="最大允许失败数")
    max_errors: int = Field(default=0, ge=0, description="最大允许错误数")


class FallbackRule(BaseModel):
    """无 JUnit 时的回退规则"""
    require_all_tools_success: bool = Field(
        default=True,
        description="是否要求所有工具调用成功"
    )


class CostGovernance(BaseModel):
    """成本治理配置（预留扩展）"""
    timeout_s: int = Field(default=300, ge=1, description="超时时间（秒）")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")


class ToolsPolicy(BaseModel):
    """工具策略配置"""
    allowlist: list[str] = Field(
        default_factory=list,
        description="允许执行的工具列表（空列表表示允许所有）"
    )


class SandboxPolicy(BaseModel):
    """沙箱策略配置 (L3 执行层隔离)

    控制 subprocess 执行的安全边界。
    默认值与 execution/sandbox.py 中的 SandboxConfig 对齐。
    """
    enabled: bool = Field(default=True, description="是否启用沙箱")
    timeout_s: int = Field(default=300, ge=1, description="硬超时（秒）")
    memory_limit_mb: int = Field(default=512, ge=64, description="内存软限制（MB）")
    allowed_paths: list[str] = Field(
        default_factory=lambda: ["tests/", "test/", "artifacts/"],
        description="路径白名单"
    )
    env_whitelist: list[str] = Field(
        default_factory=lambda: [
            "PATH", "HOME", "USER", "SHELL", "TMPDIR",
            "PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED", "VIRTUAL_ENV",
            "LANG", "LC_*",
            "CI", "GITHUB_*", "RUNNER_*", "QF_*",
        ],
        description="环境变量白名单（支持 glob）"
    )



class PolicyConfig(BaseModel):
    """策略配置主模型"""
    version: str = Field(default="1.0", description="配置版本")
    high_risk_keywords: list[str] = Field(
        default_factory=list,
        description="高危关键词列表（触发 HITL）"
    )
    high_risk_patterns: list[str] = Field(
        default_factory=list,
        description="高危正则模式列表（触发 HITL）"
    )
    junit_pass_rule: JUnitPassRule = Field(
        default_factory=JUnitPassRule,
        description="JUnit 通过规则"
    )
    fallback_rule: FallbackRule = Field(
        default_factory=FallbackRule,
        description="无 JUnit 时的回退规则"
    )
    cost_governance: CostGovernance = Field(
        default_factory=CostGovernance,
        description="成本治理配置"
    )
    tools: ToolsPolicy = Field(
        default_factory=ToolsPolicy,
        description="工具策略配置"
    )
    sandbox: SandboxPolicy = Field(
        default_factory=SandboxPolicy,
        description="沙箱策略配置"
    )


def load_policy(path: Optional[Path] = None) -> PolicyConfig:
    """加载策略配置

    优先级:
    1. 显式传入的 path
    2. 环境变量 QF_POLICY_PATH
    3. 默认路径 (governance/policy_config.yaml)
    4. 内置默认值

    Args:
        path: 策略文件路径（可选）

    Returns:
        PolicyConfig: 策略配置对象
    """
    # 确定配置文件路径
    if path is None:
        env_path = os.environ.get(ENV_POLICY_PATH)
        if env_path:
            path = Path(env_path)
        else:
            path = DEFAULT_POLICY_PATH

    # 尝试加载
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            config = PolicyConfig.model_validate(data or {})
            logger.info(f"Policy loaded from {path}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load policy from {path}: {e}, using defaults")
            return PolicyConfig()
    else:
        logger.info(f"Policy file not found at {path}, using defaults")
        return PolicyConfig()


def get_default_policy() -> PolicyConfig:
    """获取默认策略（不加载文件）

    用于测试或需要纯默认值的场景。
    """
    return PolicyConfig(
        high_risk_keywords=[
            "delete", "drop", "truncate", "remove", "destroy",
            "prod", "production", "master", "main", "release",
            "deploy", "rollback", "migration", "schema", "database", "db",
        ],
        high_risk_patterns=[
            r"\bprod\b",
            r"\bproduction\b",
            r"\bdelete\s+from\b",
            r"\bdrop\s+table\b",
            r"\btruncate\b",
            r"\brm\s+-rf\b",
            r"\bsudo\b",
        ],
    )


# 全局缓存（单例模式）
_cached_policy: Optional[PolicyConfig] = None


def get_policy(force_reload: bool = False) -> PolicyConfig:
    """获取策略配置（带缓存）

    Args:
        force_reload: 是否强制重新加载

    Returns:
        PolicyConfig: 策略配置对象
    """
    global _cached_policy
    if _cached_policy is None or force_reload:
        _cached_policy = load_policy()
    return _cached_policy


def clear_policy_cache() -> None:
    """清除策略缓存（用于测试）"""
    global _cached_policy
    _cached_policy = None
