"""Support Phase 3 import upload statuses.

Revision ID: 0003_phase_3_imports
Revises: 0002_phase_1_5_hardening
Create Date: 2026-05-13
"""
from alembic import op


revision = "0003_phase_3_imports"
down_revision = "0002_phase_1_5_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_transaction_uploads_upload_status", "transaction_uploads", type_="check")
    op.create_check_constraint(
        "ck_transaction_uploads_upload_status",
        "transaction_uploads",
        "upload_status IN ('pending', 'processing', 'completed', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_transaction_uploads_upload_status", "transaction_uploads", type_="check")
    op.create_check_constraint(
        "ck_transaction_uploads_upload_status",
        "transaction_uploads",
        "upload_status IN ('pending', 'processing', 'processed', 'failed')",
    )
