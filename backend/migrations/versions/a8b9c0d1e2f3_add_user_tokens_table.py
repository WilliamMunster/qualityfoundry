"""add_user_tokens_table

Revision ID: a8b9c0d1e2f3
Revises: 1697c6ae1fca
Create Date: 2026-01-24 11:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = '1697c6ae1fca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 user_tokens 表
    op.create_table('user_tokens',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_tokens_token_hash', 'user_tokens', ['token_hash'], unique=True)
    op.create_index('ix_user_tokens_user_id', 'user_tokens', ['user_id'], unique=False)
    op.create_index('ix_user_tokens_expires_at', 'user_tokens', ['expires_at'], unique=False)
    op.create_index('ix_user_tokens_hash_expires', 'user_tokens', ['token_hash', 'expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_tokens_hash_expires', table_name='user_tokens')
    op.drop_index('ix_user_tokens_expires_at', table_name='user_tokens')
    op.drop_index('ix_user_tokens_user_id', table_name='user_tokens')
    op.drop_index('ix_user_tokens_token_hash', table_name='user_tokens')
    op.drop_table('user_tokens')
