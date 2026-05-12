"""Create core Tally schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


uuid_type = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "transaction_uploads",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("upload_status", sa.String(length=50), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("processed_rows", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transaction_uploads_user_id", "transaction_uploads", ["user_id"])

    op.create_table(
        "transactions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("upload_id", uuid_type, nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("merchant_raw", sa.String(length=500), nullable=False),
        sa.Column("merchant_normalized", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("category_confidence", sa.Float(), nullable=True),
        sa.Column("payment_type", sa.String(length=100), nullable=True),
        sa.Column("is_recurring_candidate", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["upload_id"], ["transaction_uploads.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_category", "transactions", ["category"])
    op.create_index("ix_transactions_merchant_normalized", "transactions", ["merchant_normalized"])
    op.create_index("ix_transactions_transaction_date", "transactions", ["transaction_date"])
    op.create_index("ix_transactions_upload_id", "transactions", ["upload_id"])
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("merchant_name", sa.String(length=255), nullable=False),
        sa.Column("average_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("frequency", sa.String(length=50), nullable=False),
        sa.Column("first_seen", sa.Date(), nullable=False),
        sa.Column("last_seen", sa.Date(), nullable=False),
        sa.Column("next_expected_date", sa.Date(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_merchant_name", "subscriptions", ["merchant_name"])
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "spending_anomalies",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("anomaly_type", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("merchant_name", sa.String(length=255), nullable=True),
        sa.Column("amount_delta", sa.Numeric(12, 2), nullable=True),
        sa.Column("percentage_change", sa.Float(), nullable=True),
        sa.Column("explanation", sa.String(length=2000), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spending_anomalies_category", "spending_anomalies", ["category"])
    op.create_index("ix_spending_anomalies_merchant_name", "spending_anomalies", ["merchant_name"])
    op.create_index("ix_spending_anomalies_user_id", "spending_anomalies", ["user_id"])

    op.create_table(
        "monthly_insight_reports",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("total_spend", sa.Numeric(12, 2), nullable=False),
        sa.Column("top_categories_json", sa.JSON(), nullable=False),
        sa.Column("detected_subscriptions_json", sa.JSON(), nullable=False),
        sa.Column("anomalies_json", sa.JSON(), nullable=False),
        sa.Column("ai_summary", sa.String(length=4000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monthly_insight_reports_month", "monthly_insight_reports", ["month"])
    op.create_index("ix_monthly_insight_reports_user_id", "monthly_insight_reports", ["user_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_monthly_insight_reports_user_id", table_name="monthly_insight_reports")
    op.drop_index("ix_monthly_insight_reports_month", table_name="monthly_insight_reports")
    op.drop_table("monthly_insight_reports")
    op.drop_index("ix_spending_anomalies_user_id", table_name="spending_anomalies")
    op.drop_index("ix_spending_anomalies_merchant_name", table_name="spending_anomalies")
    op.drop_index("ix_spending_anomalies_category", table_name="spending_anomalies")
    op.drop_table("spending_anomalies")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_merchant_name", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_index("ix_transactions_upload_id", table_name="transactions")
    op.drop_index("ix_transactions_transaction_date", table_name="transactions")
    op.drop_index("ix_transactions_merchant_normalized", table_name="transactions")
    op.drop_index("ix_transactions_category", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_transaction_uploads_user_id", table_name="transaction_uploads")
    op.drop_table("transaction_uploads")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
