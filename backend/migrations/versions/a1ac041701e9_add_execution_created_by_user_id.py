"""add execution created_by_user_id

Revision ID: a1ac041701e9
Revises: a8b9c0d1e2f3
Create Date: 2026-01-24 12:01:33.621480

NOTE: SQLite 不支持 ALTER TABLE ADD CONSTRAINT，所以这里只添加列和索引，
FK 约束由 ORM 层在 PostgreSQL 生产环境中执行。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1ac041701e9'
down_revision: Union[str, None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 Execution 添加 created_by_user_id（所有权锚点）
    # SQLite 不支持 ADD CONSTRAINT，只添加列和索引
    op.add_column('executions', sa.Column('created_by_user_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_executions_created_by_user_id'), 'executions', ['created_by_user_id'], unique=False)
    
    # 为 AuditLog 添加 created_by_user_id（用于 list_runs 过滤）
    op.add_column('audit_logs', sa.Column('created_by_user_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_audit_logs_created_by_user_id'), 'audit_logs', ['created_by_user_id'], unique=False)


def downgrade() -> None:
    # 回滚 AuditLog
    op.drop_index(op.f('ix_audit_logs_created_by_user_id'), table_name='audit_logs')
    op.drop_column('audit_logs', 'created_by_user_id')
    
    # 回滚 Execution
    op.drop_index(op.f('ix_executions_created_by_user_id'), table_name='executions')
    op.drop_column('executions', 'created_by_user_id')
