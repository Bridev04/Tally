"""Harden constraints and cascade behavior.

Revision ID: 0002_phase_1_5_hardening
Revises: 0001_initial_schema
Create Date: 2026-05-12
"""
from alembic import op


revision = "0002_phase_1_5_hardening"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("transaction_uploads_user_id_fkey", "transaction_uploads", type_="foreignkey")
    op.drop_constraint("transactions_user_id_fkey", "transactions", type_="foreignkey")
    op.drop_constraint("transactions_upload_id_fkey", "transactions", type_="foreignkey")
    op.drop_constraint("subscriptions_user_id_fkey", "subscriptions", type_="foreignkey")
    op.drop_constraint("spending_anomalies_user_id_fkey", "spending_anomalies", type_="foreignkey")
    op.drop_constraint("monthly_insight_reports_user_id_fkey", "monthly_insight_reports", type_="foreignkey")
    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")

    op.create_foreign_key(
        "transaction_uploads_user_id_fkey",
        "transaction_uploads",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "transactions_user_id_fkey",
        "transactions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "transactions_upload_id_fkey",
        "transactions",
        "transaction_uploads",
        ["upload_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "subscriptions_user_id_fkey",
        "subscriptions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "spending_anomalies_user_id_fkey",
        "spending_anomalies",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "monthly_insight_reports_user_id_fkey",
        "monthly_insight_reports",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "audit_logs_user_id_fkey",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_check_constraint(
        "ck_transaction_uploads_upload_status",
        "transaction_uploads",
        "upload_status IN ('pending', 'processing', 'processed', 'failed')",
    )
    op.create_check_constraint(
        "ck_transaction_uploads_row_counts",
        "transaction_uploads",
        "total_rows >= 0 AND processed_rows >= 0 AND processed_rows <= total_rows",
    )
    op.create_check_constraint(
        "ck_transactions_category_confidence",
        "transactions",
        "category_confidence IS NULL OR (category_confidence >= 0 AND category_confidence <= 1)",
    )
    op.create_check_constraint(
        "ck_transactions_currency_length",
        "transactions",
        "length(currency) = 3",
    )
    op.create_check_constraint(
        "ck_subscriptions_average_amount_nonnegative",
        "subscriptions",
        "average_amount >= 0",
    )
    op.create_check_constraint(
        "ck_subscriptions_confidence_score",
        "subscriptions",
        "confidence_score >= 0 AND confidence_score <= 1",
    )
    op.create_check_constraint(
        "ck_subscriptions_seen_date_order",
        "subscriptions",
        "last_seen >= first_seen",
    )
    op.create_check_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        "status IN ('active', 'paused', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_spending_anomalies_severity",
        "spending_anomalies",
        "severity IN ('low', 'medium', 'high')",
    )
    op.create_check_constraint(
        "ck_monthly_insight_reports_total_spend_nonnegative",
        "monthly_insight_reports",
        "total_spend >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_monthly_insight_reports_total_spend_nonnegative",
        "monthly_insight_reports",
        type_="check",
    )
    op.drop_constraint("ck_spending_anomalies_severity", "spending_anomalies", type_="check")
    op.drop_constraint("ck_subscriptions_status", "subscriptions", type_="check")
    op.drop_constraint("ck_subscriptions_seen_date_order", "subscriptions", type_="check")
    op.drop_constraint("ck_subscriptions_confidence_score", "subscriptions", type_="check")
    op.drop_constraint("ck_subscriptions_average_amount_nonnegative", "subscriptions", type_="check")
    op.drop_constraint("ck_transactions_currency_length", "transactions", type_="check")
    op.drop_constraint("ck_transactions_category_confidence", "transactions", type_="check")
    op.drop_constraint("ck_transaction_uploads_row_counts", "transaction_uploads", type_="check")
    op.drop_constraint("ck_transaction_uploads_upload_status", "transaction_uploads", type_="check")

    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.drop_constraint("monthly_insight_reports_user_id_fkey", "monthly_insight_reports", type_="foreignkey")
    op.drop_constraint("spending_anomalies_user_id_fkey", "spending_anomalies", type_="foreignkey")
    op.drop_constraint("subscriptions_user_id_fkey", "subscriptions", type_="foreignkey")
    op.drop_constraint("transactions_upload_id_fkey", "transactions", type_="foreignkey")
    op.drop_constraint("transactions_user_id_fkey", "transactions", type_="foreignkey")
    op.drop_constraint("transaction_uploads_user_id_fkey", "transaction_uploads", type_="foreignkey")

    op.create_foreign_key(
        "audit_logs_user_id_fkey",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "monthly_insight_reports_user_id_fkey",
        "monthly_insight_reports",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "spending_anomalies_user_id_fkey",
        "spending_anomalies",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "subscriptions_user_id_fkey",
        "subscriptions",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "transactions_upload_id_fkey",
        "transactions",
        "transaction_uploads",
        ["upload_id"],
        ["id"],
    )
    op.create_foreign_key(
        "transactions_user_id_fkey",
        "transactions",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "transaction_uploads_user_id_fkey",
        "transaction_uploads",
        "users",
        ["user_id"],
        ["id"],
    )
