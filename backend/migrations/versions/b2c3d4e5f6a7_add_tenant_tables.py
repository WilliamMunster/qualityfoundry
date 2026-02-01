"""add_tenant_tables

Revision ID: b2c3d4e5f6a7
Revises: 4d080a35a5a2
Create Date: 2026-02-01 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '4d080a35a5a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 tenants 表
    op.create_table('tenants',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('slug', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('contact_email', sa.String(100), nullable=True),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('max_projects', sa.Integer(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('max_storage_mb', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)
    
    # 创建 tenant_memberships 表
    op.create_table('tenant_memberships',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user')
    )
    op.create_index('ix_tenant_memberships_user_id', 'tenant_memberships', ['user_id'], unique=False)
    op.create_index('ix_tenant_memberships_tenant_id', 'tenant_memberships', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_tenant_memberships_tenant_id', table_name='tenant_memberships')
    op.drop_index('ix_tenant_memberships_user_id', table_name='tenant_memberships')
    op.drop_table('tenant_memberships')
    op.drop_index('ix_tenants_slug', table_name='tenants')
    op.drop_table('tenants')
