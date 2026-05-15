"""Add budget leak anomaly metadata.

Revision ID: 0006_phase_7_budget_leak_anomalies
Revises: 0005_phase_5_transaction_categorization
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_phase_7_budget_leak_anomalies"
down_revision = "0005_phase_5_transaction_categorization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("spending_anomalies", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("spending_anomalies", sa.Column("period_end", sa.Date(), nullable=True))
    op.add_column("spending_anomalies", sa.Column("baseline_period_start", sa.Date(), nullable=True))
    op.add_column("spending_anomalies", sa.Column("baseline_period_end", sa.Date(), nullable=True))
    op.add_column("spending_anomalies", sa.Column("transaction_count", sa.Integer(), nullable=True))
    op.add_column(
        "spending_anomalies",
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_spending_anomalies_period_start", "spending_anomalies", ["period_start"])
    op.create_index("ix_spending_anomalies_period_end", "spending_anomalies", ["period_end"])
    op.alter_column("spending_anomalies", "metadata_json", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_spending_anomalies_period_end", table_name="spending_anomalies")
    op.drop_index("ix_spending_anomalies_period_start", table_name="spending_anomalies")
    op.drop_column("spending_anomalies", "metadata_json")
    op.drop_column("spending_anomalies", "transaction_count")
    op.drop_column("spending_anomalies", "baseline_period_end")
    op.drop_column("spending_anomalies", "baseline_period_start")
    op.drop_column("spending_anomalies", "period_end")
    op.drop_column("spending_anomalies", "period_start")
