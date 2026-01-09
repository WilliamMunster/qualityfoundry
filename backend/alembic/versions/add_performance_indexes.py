"""数据库性能优化 - 添加索引

添加常用查询字段的索引以提升性能
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_performance_indexes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """添加性能优化索引"""
    # Requirements 表索引
    op.create_index('idx_requirements_status', 'requirements', ['status'])
    op.create_index('idx_requirements_created_at', 'requirements', ['created_at'])
    
    # Scenarios 表索引
    op.create_index('idx_scenarios_requirement_id', 'scenarios', ['requirement_id'])
    op.create_index('idx_scenarios_approval_status', 'scenarios', ['approval_status'])
    
    # TestCases 表索引
    op.create_index('idx_testcases_scenario_id', 'testcases', ['scenario_id'])
    op.create_index('idx_testcases_approval_status', 'testcases', ['approval_status'])
    
    # Executions 表索引
    op.create_index('idx_executions_testcase_id', 'executions', ['testcase_id'])
    op.create_index('idx_executions_environment_id', 'executions', ['environment_id'])
    op.create_index('idx_executions_status', 'executions', ['status'])
    op.create_index('idx_executions_created_at', 'executions', ['created_at'])
    
    # Approvals 表索引
    op.create_index('idx_approvals_entity_type', 'approvals', ['entity_type'])
    op.create_index('idx_approvals_entity_id', 'approvals', ['entity_id'])
    op.create_index('idx_approvals_status', 'approvals', ['status'])
    
    # Users 表索引
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    
    # AIConfigs 表索引
    op.create_index('idx_ai_configs_provider', 'ai_configs', ['provider'])
    op.create_index('idx_ai_configs_is_active', 'ai_configs', ['is_active'])
    op.create_index('idx_ai_configs_is_default', 'ai_configs', ['is_default'])


def downgrade():
    """移除索引"""
    # Requirements
    op.drop_index('idx_requirements_status')
    op.drop_index('idx_requirements_created_at')
    
    # Scenarios
    op.drop_index('idx_scenarios_requirement_id')
    op.drop_index('idx_scenarios_approval_status')
    
    # TestCases
    op.drop_index('idx_testcases_scenario_id')
    op.drop_index('idx_testcases_approval_status')
    
    # Executions
    op.drop_index('idx_executions_testcase_id')
    op.drop_index('idx_executions_environment_id')
    op.drop_index('idx_executions_status')
    op.drop_index('idx_executions_created_at')
    
    # Approvals
    op.drop_index('idx_approvals_entity_type')
    op.drop_index('idx_approvals_entity_id')
    op.drop_index('idx_approvals_status')
    
    # Users
    op.drop_index('idx_users_username')
    op.drop_index('idx_users_role')
    op.drop_index('idx_users_is_active')
    
    # AIConfigs
    op.drop_index('idx_ai_configs_provider')
    op.drop_index('idx_ai_configs_is_active')
    op.drop_index('idx_ai_configs_is_default')
