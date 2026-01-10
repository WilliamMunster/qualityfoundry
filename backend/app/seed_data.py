"""
完整数据播种脚本
用于创建所有模块的测试数据
"""
import sys
import os
from datetime import datetime, timezone
from uuid import uuid4

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qualityfoundry.database.models import (
    Base, Requirement, Scenario, TestCase, Environment, Execution,
    Approval, ApprovalStatus, ExecutionMode, RequirementStatus
)
from qualityfoundry.database.user_models import User
from qualityfoundry.database.ai_config_models import AIConfig

# 使用应用统一的数据库配置
from qualityfoundry.database.config import engine, SessionLocal


def seed_all():
    """播种所有测试数据"""
    db = SessionLocal()
    
    try:
        print("开始播种测试数据...")
        
        # 1. 创建用户（如果不存在）
        existing_user = db.query(User).filter(User.username == "admin").first()
        if not existing_user:
            from qualityfoundry.services.auth_service import AuthService
            admin_user = User(
                id=uuid4(),
                username="admin",
                email="admin@example.com",
                password_hash=AuthService.hash_password("admin"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            print("✓ 创建管理员用户")
        
        # 2. 创建需求
        requirements = []
        for i in range(3):
            req = Requirement(
                id=uuid4(),
                title=f"测试需求 {i+1}",
                content=f"这是测试需求 {i+1} 的详细内容。\n\n功能点：\n1. 用户登录\n2. 数据验证\n3. 权限控制",
                version=f"v1.{i}",
                status=RequirementStatus.DRAFT if i == 0 else RequirementStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            requirements.append(req)
            db.add(req)
        print(f"✓ 创建 {len(requirements)} 个需求")
        db.flush()
        
        # 3. 创建场景
        scenarios = []
        for i, req in enumerate(requirements):
            for j in range(2):
                scenario = Scenario(
                    id=uuid4(),
                    requirement_id=req.id,
                    title=f"场景 {i+1}.{j+1}: 用户{['登录', '注册', '查询', '更新', '删除', '导出'][j % 6]}功能",
                    description=f"验证需求 {i+1} 的第 {j+1} 个业务流程",
                    steps=[
                        f"步骤1: 打开系统页面",
                        f"步骤2: 输入测试数据",
                        f"步骤3: 点击操作按钮",
                        f"步骤4: 验证返回结果"
                    ],
                    approval_status=ApprovalStatus.PENDING if j == 0 else ApprovalStatus.APPROVED,
                    created_at=datetime.now(timezone.utc)
                )
                scenarios.append(scenario)
                db.add(scenario)
        print(f"✓ 创建 {len(scenarios)} 个场景")
        db.flush()
        
        # 4. 创建用例
        testcases = []
        for i, scenario in enumerate(scenarios[:4]):  # 只为前4个场景创建用例
            for j in range(2):
                testcase = TestCase(
                    id=uuid4(),
                    scenario_id=scenario.id,
                    title=f"用例 {i+1}.{j+1}: {['正向', '异常', '边界', '性能'][j % 4]}测试",
                    steps=[
                        f"前置条件: 系统正常运行",
                        f"操作步骤1: 执行测试操作",
                        f"操作步骤2: 验证系统响应",
                        f"预期结果: 符合业务规则"
                    ],
                    approval_status=ApprovalStatus.PENDING if j == 0 else ApprovalStatus.APPROVED,
                    created_at=datetime.now(timezone.utc)
                )
                testcases.append(testcase)
                db.add(testcase)
        print(f"✓ 创建 {len(testcases)} 个用例")
        db.flush()
        
        # 5. 创建环境
        environments = []
        env_configs = [
            {"name": "开发环境", "base_url": "http://dev.example.com"},
            {"name": "测试环境", "base_url": "http://test.example.com"},
            {"name": "预发布环境", "base_url": "http://staging.example.com"},
        ]
        for config in env_configs:
            env = Environment(
                id=uuid4(),
                name=config["name"],
                base_url=config["base_url"],
                variables={"timeout": "30", "retry": "3"},
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            environments.append(env)
            db.add(env)
        print(f"✓ 创建 {len(environments)} 个环境")
        db.flush()
        
        # 6. 创建执行记录
        from qualityfoundry.database.models import ExecutionStatus
        executions = []
        statuses = [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.SUCCESS, ExecutionStatus.FAILED]
        for i, tc in enumerate(testcases[:4]):
            execution = Execution(
                id=uuid4(),
                testcase_id=tc.id,
                environment_id=environments[i % len(environments)].id,
                mode=ExecutionMode.DSL if i % 2 == 0 else ExecutionMode.MCP,
                status=statuses[i % len(statuses)],
                result={"passed": i % 2 == 0, "duration": 1.5 + i * 0.5} if statuses[i % len(statuses)] in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED] else None,
                evidence=[{"type": "log", "content": f"执行步骤 {i+1} 完成"}] if i < 3 else [],
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc) if statuses[i % len(statuses)] in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED] else None
            )
            executions.append(execution)
            db.add(execution)
        print(f"✓ 创建 {len(executions)} 个执行记录")
        db.flush()
        
        # 7. 创建审核记录
        approvals = []
        for i, scenario in enumerate(scenarios[:3]):
            approval = Approval(
                id=uuid4(),
                entity_type="scenario",
                entity_id=scenario.id,
                status=ApprovalStatus.PENDING if i == 0 else ApprovalStatus.APPROVED,
                reviewer="admin" if i > 0 else None,
                review_comment="审核通过" if i > 0 else None,
                reviewed_at=datetime.now(timezone.utc) if i > 0 else None,
                created_at=datetime.now(timezone.utc)
            )
            approvals.append(approval)
            db.add(approval)
        print(f"✓ 创建 {len(approvals)} 个审核记录")
        
        # 8. 创建 AI 配置
        existing_ai_config = db.query(AIConfig).first()
        if not existing_ai_config:
            ai_config = AIConfig(
                id=uuid4(),
                name="默认 OpenAI 配置",
                provider="openai",
                model="gpt-4",
                api_key="sk-test-key-placeholder",
                base_url="https://api.openai.com/v1",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.add(ai_config)
            print("✓ 创建 AI 配置")
        
        db.commit()
        print("\n✅ 所有测试数据播种完成！")
        
        # 打印统计
        print("\n📊 数据统计:")
        print(f"   需求: {db.query(Requirement).count()} 条")
        print(f"   场景: {db.query(Scenario).count()} 条")
        print(f"   用例: {db.query(TestCase).count()} 条")
        print(f"   环境: {db.query(Environment).count()} 条")
        print(f"   执行: {db.query(Execution).count()} 条")
        print(f"   审核: {db.query(Approval).count()} 条")
        print(f"   用户: {db.query(User).count()} 条")
        print(f"   AI配置: {db.query(AIConfig).count()} 条")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 播种失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
