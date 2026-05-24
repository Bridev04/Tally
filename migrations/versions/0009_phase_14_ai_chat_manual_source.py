"""Allow Phase 14 AI-assisted manual transaction source.

Revision ID: 0009_phase_14_ai_chat_manual_source
Revises: 0008_phase_12_demo_markers
"""

from collections.abc import Sequence

from alembic import op


revision = "0009_phase_14_ai_chat_manual_source"
down_revision = "0008_phase_12_demo_markers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_transactions_source", "transactions", type_="check")
    op.drop_constraint("ck_transaction_uploads_source", "transaction_uploads", type_="check")
    op.create_check_constraint(
        "ck_transaction_uploads_source",
        "transaction_uploads",
        "source IN ('csv', 'manual', 'paste', 'demo', 'ai_chat_manual')",
    )
    op.create_check_constraint(
        "ck_transactions_source",
        "transactions",
        "source IN ('csv', 'manual', 'paste', 'demo', 'ai_chat_manual')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_transactions_source", "transactions", type_="check")
    op.drop_constraint("ck_transaction_uploads_source", "transaction_uploads", type_="check")
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
