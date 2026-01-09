"""
阶段2功能自测脚本

测试：
1. 审核流程（创建、批准、拒绝）
2. 场景管理（CRUD）
3. 场景审核集成
"""
import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path / "app"))

from qualityfoundry.database.config import SessionLocal  # noqa: E402
from qualityfoundry.database.models import (  # noqa: E402
    ApprovalStatus as DBApprovalStatus,
    Requirement,
    Scenario,
)
from qualityfoundry.services.approval_service import ApprovalService  # noqa: E402


def test_approval_workflow():
    """测试审核流程"""
    print("=" * 50)
    print("测试1: 审核流程")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # 1. 创建测试需求
        print("\n1. 创建测试需求...")
        requirement = Requirement(
            title="测试需求",
            content="用于测试审核流程",
            version="v1.0"
        )
        db.add(requirement)
        db.commit()
        db.refresh(requirement)
        print(f"✅ 需求创建成功，ID: {requirement.id}")
        
        # 2. 创建测试场景
        print("\n2. 创建测试场景...")
        scenario = Scenario(
            requirement_id=requirement.id,
            title="测试场景",
            description="用于测试审核流程",
            steps=["步骤1", "步骤2"],
            approval_status=DBApprovalStatus.PENDING,
            version="v1.0"
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        print(f"✅ 场景创建成功，ID: {scenario.id}")
        print(f"✅ 初始审核状态: {scenario.approval_status}")
        
        # 3. 创建审核记录
        print("\n3. 创建审核记录...")
        approval_service = ApprovalService(db)
        approval = approval_service.create_approval(
            entity_type="scenario",
            entity_id=scenario.id,
            reviewer="test_reviewer"
        )
        print(f"✅ 审核记录创建成功，ID: {approval.id}")
        print(f"✅ 审核状态: {approval.status}")
        
        # 4. 批准审核
        print("\n4. 批准审核...")
        approved = approval_service.approve(
            approval_id=approval.id,
            reviewer="test_reviewer",
            comment="测试批准"
        )
        print("✅ 审核批准成功")
        print(f"✅ 审核状态: {approved.status}")
        print(f"✅ 审核人: {approved.reviewer}")
        print(f"✅ 审核意见: {approved.review_comment}")
        
        # 5. 验证场景状态更新
        db.refresh(scenario)
        print("\n5. 验证场景状态...")
        print(f"✅ 场景审核状态: {scenario.approval_status}")
        print(f"✅ 场景审核人: {scenario.approved_by}")
        
        if scenario.approval_status == DBApprovalStatus.APPROVED:
            print("✅ 场景状态更新成功")
        else:
            print("❌ 场景状态更新失败")
            return False
        
        # 清理
        db.delete(approval)
        db.delete(scenario)
        db.delete(requirement)
        db.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ 审核流程测试失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_scenario_crud():
    """测试场景 CRUD"""
    print("\n" + "=" * 50)
    print("测试2: 场景 CRUD")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # 1. 创建需求
        print("\n1. 创建需求...")
        requirement = Requirement(
            title="测试需求",
            content="用于测试场景 CRUD",
            version="v1.0"
        )
        db.add(requirement)
        db.commit()
        db.refresh(requirement)
        print("✅ 需求创建成功")
        
        # 2. 创建场景
        print("\n2. 创建场景...")
        scenario = Scenario(
            requirement_id=requirement.id,
            title="测试场景",
            description="测试描述",
            steps=["步骤1", "步骤2", "步骤3"],
            version="v1.0"
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        print(f"✅ 场景创建成功，ID: {scenario.id}")
        print(f"✅ 步骤数量: {len(scenario.steps)}")
        
        # 3. 查询场景
        print("\n3. 查询场景...")
        found = db.query(Scenario).filter(Scenario.id == scenario.id).first()
        if found and found.title == "测试场景":
            print(f"✅ 场景查询成功: {found.title}")
        else:
            print("❌ 场景查询失败")
            return False
        
        # 4. 更新场景
        print("\n4. 更新场景...")
        found.title = "更新后的测试场景"
        found.steps = ["新步骤1", "新步骤2"]
        db.commit()
        db.refresh(found)
        print(f"✅ 场景更新成功: {found.title}")
        print(f"✅ 新步骤数量: {len(found.steps)}")
        
        # 5. 删除场景
        print("\n5. 删除场景...")
        db.delete(found)
        db.delete(requirement)
        db.commit()
        print("✅ 场景删除成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 场景 CRUD 测试失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_scenario_approval_integration():
    """测试场景审核集成"""
    print("\n" + "=" * 50)
    print("测试3: 场景审核集成")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # 1. 创建需求和场景
        print("\n1. 创建需求和场景...")
        requirement = Requirement(
            title="测试需求",
            content="用于测试场景审核集成",
            version="v1.0"
        )
        db.add(requirement)
        db.commit()
        
        scenario = Scenario(
            requirement_id=requirement.id,
            title="待审核场景",
            description="测试审核集成",
            steps=["步骤1"],
            approval_status=DBApprovalStatus.PENDING,
            version="v1.0"
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        print(f"✅ 场景创建成功，状态: {scenario.approval_status}")
        
        # 2. 创建审核并批准
        print("\n2. 创建审核并批准...")
        approval_service = ApprovalService(db)
        approval = approval_service.create_approval(
            entity_type="scenario",
            entity_id=scenario.id
        )
        
        approval_service.approve(
            approval_id=approval.id,
            reviewer="integration_tester",
            comment="集成测试批准"
        )
        print("✅ 审核批准成功")
        
        # 3. 验证场景状态
        db.refresh(scenario)
        print("\n3. 验证场景状态...")
        print(f"✅ 场景状态: {scenario.approval_status}")
        print(f"✅ 审核人: {scenario.approved_by}")
        
        if (scenario.approval_status == DBApprovalStatus.APPROVED and 
            scenario.approved_by == "integration_tester"):
            print("✅ 场景审核集成成功")
            result = True
        else:
            print("❌ 场景审核集成失败")
            result = False
        
        # 清理
        db.delete(approval)
        db.delete(scenario)
        db.delete(requirement)
        db.commit()
        
        return result
        
    except Exception as e:
        print(f"❌ 场景审核集成测试失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("阶段2功能自测")
    print("=" * 50)
    
    results = []
    
    # 测试1: 审核流程
    results.append(("审核流程", test_approval_workflow()))
    
    # 测试2: 场景 CRUD
    results.append(("场景 CRUD", test_scenario_crud()))
    
    # 测试3: 场景审核集成
    results.append(("场景审核集成", test_scenario_approval_integration()))
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！阶段2功能验证成功！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())
