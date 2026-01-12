"""
阶段1功能自测脚本

测试：
1. 数据库连接
2. 需求管理 API
3. 文件上传服务
"""
import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path / "app"))

from qualityfoundry.database.config import engine, SessionLocal  # noqa: E402
from qualityfoundry.database.models import Requirement  # noqa: E402
from sqlalchemy import inspect  # noqa: E402


def _run_database_connection():
    """测试数据库连接"""
    print("=" * 50)
    print("测试1: 数据库连接")
    print("=" * 50)
    
    try:
        # 检查数据库表
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("✅ 数据库连接成功")
        print(f"✅ 发现 {len(tables)} 个数据表:")
        for table in tables:
            print(f"   - {table}")
        
        # 检查必要的表
        required_tables = ["requirements", "scenarios", "testcases", "environments", "executions", "approvals"]
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"❌ 缺少数据表: {', '.join(missing_tables)}")
            return False
        else:
            print("✅ 所有必要的数据表都存在")
            return True
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def _run_requirement_crud():
    """测试需求 CRUD 操作"""
    print("\n" + "=" * 50)
    print("测试2: 需求 CRUD 操作")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # 创建需求
        print("\n1. 创建需求...")
        requirement = Requirement(
            title="测试需求",
            content="这是一个测试需求的内容",
            version="v1.0",
            created_by="test_user"
        )
        db.add(requirement)
        db.commit()
        db.refresh(requirement)
        print(f"✅ 创建成功，ID: {requirement.id}")
        
        # 查询需求
        print("\n2. 查询需求...")
        found = db.query(Requirement).filter(Requirement.id == requirement.id).first()
        if found:
            print(f"✅ 查询成功: {found.title}")
        else:
            print("❌ 查询失败")
            return False
        
        # 更新需求
        print("\n3. 更新需求...")
        found.title = "更新后的测试需求"
        db.commit()
        db.refresh(found)
        print(f"✅ 更新成功: {found.title}")
        
        # 删除需求
        print("\n4. 删除需求...")
        db.delete(found)
        db.commit()
        print("✅ 删除成功")
        
        # 验证删除
        deleted = db.query(Requirement).filter(Requirement.id == requirement.id).first()
        if deleted is None:
            print("✅ 验证删除成功")
            return True
        else:
            print("❌ 删除验证失败")
            return False
            
    except Exception as e:
        print(f"❌ CRUD 操作失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def _run_file_upload_service():
    """测试文件上传服务"""
    print("\n" + "=" * 50)
    print("测试3: 文件上传服务")
    print("=" * 50)
    
    try:
        from qualityfoundry.services.file_upload import FileUploadService
        
        service = FileUploadService()
        print("✅ 文件上传服务初始化成功")
        print(f"✅ 上传目录: {service.upload_dir}")
        print(f"✅ 支持的文件类型: {', '.join(service.allowed_extensions)}")
        print(f"✅ 最大文件大小: {service.max_file_size / 1024 / 1024:.1f} MB")
        
        # 检查上传目录是否存在
        if service.upload_dir.exists():
            print("✅ 上传目录已创建")
        else:
            print("❌ 上传目录不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 文件上传服务测试失败: {e}")
        return False


def test_database_connection():
    """测试数据库连接"""
    assert _run_database_connection()


def test_requirement_crud():
    """测试需求 CRUD 操作"""
    assert _run_requirement_crud()


def test_file_upload_service():
    """测试文件上传服务"""
    assert _run_file_upload_service()


def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("阶段1功能自测")
    print("=" * 50)
    
    results = []
    
    # 测试1: 数据库连接
    results.append(("数据库连接", _run_database_connection()))
    
    # 测试2: 需求 CRUD
    results.append(("需求 CRUD", _run_requirement_crud()))
    
    # 测试3: 文件上传服务
    results.append(("文件上传服务", _run_file_upload_service()))
    
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
        print("\n🎉 所有测试通过！阶段1功能验证成功！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())
