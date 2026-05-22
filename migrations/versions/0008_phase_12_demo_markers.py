"""Add Phase 12 demo data markers.

Revision ID: 0008_phase_12_demo_markers
Revises: 0007_phase_9_monthly_reports
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision = "0008_phase_12_demo_markers"
down_revision = "0007_phase_9_monthly_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transaction_uploads",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="csv"),
    )
    op.add_column(
        "transaction_uploads",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("transaction_uploads", sa.Column("demo_scenario", sa.String(length=50), nullable=True))
    op.add_column("transactions", sa.Column("source", sa.String(length=20), nullable=False, server_default="csv"))
    op.add_column("transactions", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("transactions", sa.Column("demo_scenario", sa.String(length=50), nullable=True))

    op.execute("UPDATE transaction_uploads SET source = 'manual' WHERE file_name = 'manual-entry'")
    op.execute("UPDATE transaction_uploads SET source = 'paste' WHERE file_name = 'paste-import'")
    op.execute(
        "UPDATE transaction_uploads SET source = 'demo', is_demo = 1, demo_scenario = 'full_portfolio' "
        "WHERE file_name = 'synthetic-demo-data'"
    )
    op.execute(
        "UPDATE transactions SET source = (SELECT transaction_uploads.source FROM transaction_uploads "
        "WHERE transaction_uploads.id = transactions.upload_id)"
    )
    op.execute(
        "UPDATE transactions SET is_demo = 1, demo_scenario = 'full_portfolio' "
        "WHERE upload_id IN (SELECT id FROM transaction_uploads WHERE is_demo = 1)"
    )

    op.create_check_constraint(
        "ck_transaction_uploads_source",
        "transaction_uploads",
        "source IN ('csv', 'manual', 'paste', 'demo')",
    )
    op.create_check_constraint(
        "ck_transactions_source",
        "transactions",
        "source IN ('csv', 'manual', 'paste', 'demo')",
    )
    op.create_index("ix_transaction_uploads_source", "transaction_uploads", ["source"])
    op.create_index("ix_transaction_uploads_is_demo", "transaction_uploads", ["is_demo"])
    op.create_index("ix_transaction_uploads_demo_scenario", "transaction_uploads", ["demo_scenario"])
    op.create_index("ix_transactions_source", "transactions", ["source"])
    op.create_index("ix_transactions_is_demo", "transactions", ["is_demo"])
    op.create_index("ix_transactions_demo_scenario", "transactions", ["demo_scenario"])

    op.alter_column("transaction_uploads", "source", server_default=None)
    op.alter_column("transaction_uploads", "is_demo", server_default=None)
    op.alter_column("transactions", "source", server_default=None)
    op.alter_column("transactions", "is_demo", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_transactions_demo_scenario", table_name="transactions")
    op.drop_index("ix_transactions_is_demo", table_name="transactions")
    op.drop_index("ix_transactions_source", table_name="transactions")
    op.drop_index("ix_transaction_uploads_demo_scenario", table_name="transaction_uploads")
    op.drop_index("ix_transaction_uploads_is_demo", table_name="transaction_uploads")
    op.drop_index("ix_transaction_uploads_source", table_name="transaction_uploads")
    op.drop_constraint("ck_transactions_source", "transactions", type_="check")
    op.drop_constraint("ck_transaction_uploads_source", "transaction_uploads", type_="check")
    op.drop_column("transactions", "demo_scenario")
    op.drop_column("transactions", "is_demo")
    op.drop_column("transactions", "source")
    op.drop_column("transaction_uploads", "demo_scenario")
    op.drop_column("transaction_uploads", "is_demo")
    op.drop_column("transaction_uploads", "source")
