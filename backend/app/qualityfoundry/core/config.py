"""QualityFoundry - Settings（全局配置）

原则：
- 所有运行期可配置项集中在这里，形成稳定“配置契约”
- 保留历史字段名以兼容旧代码（例如 DB_URL）
- 提供合理默认值，保证本地/CI 开箱即用
"""

from __future__ import annotations
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置对象（可通过环境变量 / .env 覆盖）"""

    model_config = SettingsConfigDict(
        env_prefix="QF_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- 数据库 ----------
    # 兼容旧代码：core/db.py 读取 settings.DB_URL
    # 环境变量：QF_DB_URL
    # 默认为 None，以便在 database/config.py 中根据运行环境自动计算绝对路径
    DB_URL: Optional[str] = None

    # ---------- 执行产物 ----------
    # 执行证据、截图、日志、报告等的输出目录
    # 环境变量：QF_ARTIFACTS_DIR
    artifacts_dir: str = "artifacts"

    # ---------- 认证 ----------
    # Token 混淆盐（建议生产环境通过环境变量设置）
    # 环境变量：QF_TOKEN_PEPPER
    TOKEN_PEPPER: str = "qf_default_pepper_change_in_prod"
    
    # Token 过期时间（小时）
    # 环境变量：QF_TOKEN_EXPIRE_HOURS
    TOKEN_EXPIRE_HOURS: int = 24
    
    # ---------- Token 清理 ----------
    # 启动时是否清理过期 token（生产环境建议开启）
    # 环境变量：QF_TOKEN_CLEANUP_ENABLED
    TOKEN_CLEANUP_ENABLED: bool = False
    
    # 已撤销 token 保留天数
    # 环境变量：QF_TOKEN_CLEANUP_RETENTION_DAYS
    TOKEN_CLEANUP_RETENTION_DAYS: int = 7


# 全局单例：直接 import settings 使用
settings = Settings()
