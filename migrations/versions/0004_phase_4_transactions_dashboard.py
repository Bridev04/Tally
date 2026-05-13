"""Add manual transaction category marker.

Revision ID: 0004_phase_4_transactions_dashboard
Revises: 0003_phase_3_imports
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_phase_4_transactions_dashboard"
down_revision = "0003_phase_3_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("category_manually_set", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("transactions", "category_manually_set", server_default=None)


def downgrade() -> None:
    op.drop_column("transactions", "category_manually_set")
