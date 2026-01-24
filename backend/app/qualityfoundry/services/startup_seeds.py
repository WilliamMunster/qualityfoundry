"""QualityFoundry - Startup Seeding

后端启动时自动 seed 默认数据，解决空库导致前端不可用的问题。
"""
from sqlalchemy.orm import Session

from qualityfoundry.database.models import Environment


def seed_default_environment(db: Session) -> None:
    """若 environments 表为空，插入默认 Local 环境。
    
    解决问题：新用户首次使用时，环境下拉框为空导致无法发起运行。
    """
    existing = db.query(Environment).first()
    if existing:
        return  # 已有数据，不做处理
    
    local_env = Environment(
        name="Local",
        base_url="http://localhost",
        variables={"debug": True, "env": "local"},
        health_check_url="http://localhost/health",
        is_active=True,
    )
    db.add(local_env)
    db.commit()


def run_startup_seeds(db: Session) -> None:
    """运行所有启动时 seed 逻辑。"""
    seed_default_environment(db)
