"""Add deterministic transaction categorization metadata.

Revision ID: 0005_phase_5_transaction_categorization
Revises: 0004_phase_4_transactions_dashboard
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_phase_5_transaction_categorization"
down_revision = "0004_phase_4_transactions_dashboard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("category_source", sa.String(length=20), nullable=False, server_default="unknown"),
    )
    op.add_column("transactions", sa.Column("categorization_reason", sa.String(length=500), nullable=True))
    op.add_column("transactions", sa.Column("categorization_rule", sa.String(length=255), nullable=True))
    op.create_index("ix_transactions_category_source", "transactions", ["category_source"])
    op.create_check_constraint(
        "ck_transactions_category_source",
        "transactions",
        "category_source IN ('auto', 'manual', 'imported', 'unknown')",
    )
    op.execute("UPDATE transactions SET category_source = 'manual' WHERE category_manually_set = true")
    op.execute(
        "UPDATE transactions SET category_source = 'imported' "
        "WHERE category_manually_set = false AND category IS NOT NULL"
    )
    op.alter_column("transactions", "category_source", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_transactions_category_source", "transactions", type_="check")
    op.drop_index("ix_transactions_category_source", table_name="transactions")
    op.drop_column("transactions", "categorization_rule")
    op.drop_column("transactions", "categorization_reason")
    op.drop_column("transactions", "category_source")
