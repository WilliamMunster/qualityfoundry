"""QualityFoundry - 所有权验证服务

提供 run/execution 的所有权检查功能。

## 架构说明：双锚点设计

所有权以 **Execution.created_by_user_id** 为唯一权威（Primary）。
AuditLog.created_by_user_id 仅用于 list_runs 查询加速（Secondary）。

**鉴权规则**：
- 任何资源访问控制判断必须以 Execution 表为准
- AuditLog 的 owner 字段仅供溯源和查询优化，不得作为唯一判断依据
- 若资源无对应 Execution 记录，只有 ADMIN 可访问
"""
from uuid import UUID
from sqlalchemy.orm import Session

from qualityfoundry.database.models import Execution
from qualityfoundry.database.user_models import User, UserRole


def check_run_ownership(db: Session, run_id: UUID, user: User) -> bool:
    """检查用户是否有权访问指定 run_id
    
    规则：
    - ADMIN 可访问所有 run
    - 其他用户只能访问自己创建的 run（created_by_user_id == user.id）
    - 若 run 无 owner（历史数据），只有 ADMIN 可访问
    
    Args:
        db: 数据库会话
        run_id: 运行 ID
        user: 当前用户
        
    Returns:
        是否有访问权限
    """
    if user.role == UserRole.ADMIN:
        return True
    
    # 从 Execution 表查找 owner
    execution = db.query(Execution).filter(Execution.id == run_id).first()
    
    if not execution:
        # 若执行记录不存在，拒绝访问
        return False
    
    # 检查所有权
    if execution.created_by_user_id is None:
        # 历史数据无 owner，只有 ADMIN 可访问（已在上面处理）
        return False
    
    return execution.created_by_user_id == user.id


def check_execution_ownership(db: Session, execution_id: UUID, user: User) -> bool:
    """检查用户是否有权访问指定执行记录
    
    与 check_run_ownership 相同逻辑，但语义更明确。
    """
    return check_run_ownership(db, execution_id, user)
