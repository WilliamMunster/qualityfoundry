"""QualityFoundry - Database Configuration

数据库连接配置
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from qualityfoundry.core.config import settings

from pathlib import Path

# 创建 Base 类
Base = declarative_base()

# 数据库 URL
# 支持 SQLite（开发）和 PostgreSQL（生产）
# 计算项目根目录 (app/qualityfoundry/database/config.py -> ... -> root)
BASE_DIR = Path(__file__).resolve().parents[4]
DATABASE_URL = getattr(settings, "database_url", f"sqlite:///{BASE_DIR / 'qualityfoundry.db'}")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    echo=getattr(settings, "database_echo", False),
    # SQLite 特殊配置
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# 创建 Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
