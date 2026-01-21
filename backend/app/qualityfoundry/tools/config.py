"""QualityFoundry - Tool Configuration

统一的工具配置常量，确保路径约定在所有工具中一致。

路径结构约定：
    {ARTIFACTS_ROOT}/{run_id}/
    ├── tools/
    │   ├── run_playwright/
    │   │   ├── step_000.png
    │   │   ├── step_001.png
    │   │   └── trace.zip
    │   ├── run_pytest/
    │   │   └── junit.xml
    │   └── fetch_logs/
    │       └── log.jsonl
    └── evidence.json         # PR-3 产出
"""

from pathlib import Path

# Artifact 根目录（相对于项目根目录）
# 可通过环境变量 QF_ARTIFACTS_ROOT 覆盖
ARTIFACTS_ROOT = Path("artifacts")

# 敏感字段列表（日志脱敏用）
REDACT_KEYS = frozenset({
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "cookie",
    "authorization",
    "auth",
    "credential",
    "credentials",
})

# 最大输出截断长度（避免日志过大）
MAX_STDOUT_LENGTH = 10000
MAX_STDERR_LENGTH = 10000
MAX_ARG_VALUE_LENGTH = 1000


def get_artifacts_root() -> Path:
    """获取 artifacts 根目录（支持环境变量覆盖）"""
    import os
    env_root = os.environ.get("QF_ARTIFACTS_ROOT")
    if env_root:
        return Path(env_root)
    return ARTIFACTS_ROOT


def redact_sensitive(data: dict, keys: frozenset | None = None) -> dict:
    """脱敏字典中的敏感字段

    Args:
        data: 原始字典
        keys: 敏感字段名集合（默认使用 REDACT_KEYS）

    Returns:
        脱敏后的字典副本
    """
    keys = keys or REDACT_KEYS
    result = {}
    for k, v in data.items():
        if k.lower() in keys:
            result[k] = "[REDACTED]"
        elif isinstance(v, dict):
            result[k] = redact_sensitive(v, keys)
        elif isinstance(v, str) and len(v) > MAX_ARG_VALUE_LENGTH:
            result[k] = v[:MAX_ARG_VALUE_LENGTH] + f"...[truncated, total {len(v)} chars]"
        else:
            result[k] = v
    return result


def truncate_output(text: str | None, max_length: int = MAX_STDOUT_LENGTH) -> str | None:
    """截断过长输出"""
    if text is None:
        return None
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"\n...[truncated, total {len(text)} chars]"
