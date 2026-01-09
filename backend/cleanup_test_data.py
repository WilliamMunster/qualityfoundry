"""
测试数据清理工具
"""
import os
import glob


def cleanup_test_databases():
    """清理测试数据库文件"""
    test_db_patterns = [
        "test_*.db",
        "test_*.db-shm",
        "test_*.db-wal",
    ]
    
    cleaned_files = []
    for pattern in test_db_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                cleaned_files.append(file_path)
                print(f"✅ 已删除: {file_path}")
            except Exception as e:
                print(f"❌ 删除失败 {file_path}: {e}")
    
    if cleaned_files:
        print(f"\n🎉 共清理 {len(cleaned_files)} 个测试数据库文件")
    else:
        print("✨ 没有找到需要清理的测试数据库文件")


if __name__ == "__main__":
    cleanup_test_databases()
