"""add_audit_logs_table

Revision ID: 1697c6ae1fca
Revises: af9a5ed80930
Create Date: 2026-01-23 21:28:51.884347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1697c6ae1fca'
down_revision: Union[str, None] = 'af9a5ed80930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 audit_logs 表
    op.create_table('audit_logs',
    sa.Column('id', sa.String(36), nullable=False),
    sa.Column('run_id', sa.String(36), nullable=False),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.Column('event_type', sa.String(50), nullable=False),
    sa.Column('actor', sa.String(255), nullable=True),
    sa.Column('tool_name', sa.String(255), nullable=True),
    sa.Column('args_hash', sa.String(64), nullable=True),
    sa.Column('status', sa.String(50), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('policy_hash', sa.String(64), nullable=True),
    sa.Column('git_sha', sa.String(64), nullable=True),
    sa.Column('decision_source', sa.String(100), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_run_id'), 'audit_logs', ['run_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_ts'), 'audit_logs', ['ts'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_ts'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_run_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_table('audit_logs')
