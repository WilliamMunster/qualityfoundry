"""Add seq_id columns to requirements, scenarios, testcases

Revision ID: add_seq_id_columns
Revises: e005e747fc14
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_seq_id_columns'
down_revision: Union[str, None] = 'e005e747fc14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add seq_id columns
    op.add_column('requirements', sa.Column('seq_id', sa.Integer(), nullable=True))
    op.add_column('scenarios', sa.Column('seq_id', sa.Integer(), nullable=True))
    op.add_column('testcases', sa.Column('seq_id', sa.Integer(), nullable=True))
    
    # Create indexes
    op.create_index('ix_requirements_seq_id', 'requirements', ['seq_id'], unique=True)
    op.create_index('ix_scenarios_seq_id', 'scenarios', ['seq_id'], unique=False)
    op.create_index('ix_testcases_seq_id', 'testcases', ['seq_id'], unique=False)
    
    # Backfill seq_id for existing records
    # Requirements
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id FROM requirements ORDER BY created_at"))
    for i, row in enumerate(result, 1):
        conn.execute(sa.text("UPDATE requirements SET seq_id = :seq WHERE id = :id"), {"seq": i, "id": row[0]})
    
    # Scenarios
    result = conn.execute(sa.text("SELECT id FROM scenarios ORDER BY created_at"))
    for i, row in enumerate(result, 1):
        conn.execute(sa.text("UPDATE scenarios SET seq_id = :seq WHERE id = :id"), {"seq": i, "id": row[0]})
    
    # TestCases
    result = conn.execute(sa.text("SELECT id FROM testcases ORDER BY created_at"))
    for i, row in enumerate(result, 1):
        conn.execute(sa.text("UPDATE testcases SET seq_id = :seq WHERE id = :id"), {"seq": i, "id": row[0]})


def downgrade() -> None:
    op.drop_index('ix_testcases_seq_id', table_name='testcases')
    op.drop_index('ix_scenarios_seq_id', table_name='scenarios')
    op.drop_index('ix_requirements_seq_id', table_name='requirements')
    op.drop_column('testcases', 'seq_id')
    op.drop_column('scenarios', 'seq_id')
    op.drop_column('requirements', 'seq_id')
