"""
QualityFoundry 测试配置

统一管理测试数据库初始化，确保所有模型都被导入和注册。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qualityfoundry.database.config import Base, get_db
from qualityfoundry.database import models  # noqa: F401 - 注册主模型
from qualityfoundry.database import user_models  # noqa: F401 - 注册用户模型
from qualityfoundry.database import ai_config_models  # noqa: F401 - 注册 AI 配置模型
from qualityfoundry.database import system_config_models  # noqa: F401 - 注册系统配置模型
from qualityfoundry.main import app

# 使用文件数据库进行测试（内存数据库有连接隔离问题）
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# 覆盖应用的数据库依赖
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前创建所有表，测试后清理"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """提供测试客户端"""
    from fastapi.testclient import TestClient
    return TestClient(app)
