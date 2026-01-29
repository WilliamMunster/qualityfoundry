"""add run_events table for sse

Revision ID: 4d080a35a5a2
Revises: a1ac041701e9
Create Date: 2026-01-29 22:22:08.576648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4d080a35a5a2'
down_revision: Union[str, None] = 'a1ac041701e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 run_events 表用于 SSE 事件流"""
    op.create_table(
        'run_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('data', sa.Text(), nullable=True),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False, index=True, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    """删除 run_events 表"""
    op.drop_table('run_events')
