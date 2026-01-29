"""
QualityFoundry 测试配置

统一管理测试数据库初始化，确保所有模型都被导入和注册。
"""
import pytest
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qualityfoundry.database.config import Base, get_db
from qualityfoundry.database import models  # noqa: F401 - 注册主模型
from qualityfoundry.database import user_models  # noqa: F401 - 注册用户模型
from qualityfoundry.database import ai_config_models  # noqa: F401 - 注册 AI 配置模型
from qualityfoundry.database import system_config_models  # noqa: F401 - 注册系统配置模型
from qualityfoundry.database import audit_log_models  # noqa: F401 - 注册审计日志模型
from qualityfoundry.database import token_models  # noqa: F401 - 注册 Token 模型
from qualityfoundry.database.user_models import User, UserRole
from qualityfoundry.api.deps.auth_deps import get_current_user
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


@pytest.fixture
def db():
    """提供数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 创建 Mock Admin 用户（用于测试）
MOCK_ADMIN_USER = User(
    id=uuid4(),
    username="test_admin",
    password_hash="mock_hash",
    email="test@example.com",
    full_name="Test Admin",
    role=UserRole.ADMIN,
    is_active=True,
)


def override_get_current_user():
    """覆盖认证依赖，返回 Mock Admin 用户"""
    return MOCK_ADMIN_USER


# 默认覆盖（作为兜底）
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture(autouse=True)
def apply_overrides():
    """每个测试自动应用依赖覆盖，并在结束后清理"""
    # 先保存原始状态（如果需要）
    old_overrides = app.dependency_overrides.copy()
    
    # 强制重新设置覆盖（防止被其他测试清理）
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    yield
    
    # 恢复状态，但不建议直接 clear()，因为可能影响并行
    app.dependency_overrides = old_overrides


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


@pytest.fixture
def mock_admin_user():
    """提供 Mock Admin 用户 fixture"""
    return MOCK_ADMIN_USER


@pytest.fixture
def mock_viewer_user():
    """提供 Mock Viewer 用户 fixture"""
    return User(
        id=uuid4(),
        username="test_viewer",
        password_hash="mock_hash",
        email="viewer@example.com",
        full_name="Test Viewer",
        role=UserRole.VIEWER,
        is_active=True,
    )

