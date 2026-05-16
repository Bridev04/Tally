"""Add monthly report generation metadata.

Revision ID: 0007_phase_9_monthly_reports
Revises: 0006_phase_7_budget_leak_anomalies
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_phase_9_monthly_reports"
down_revision = "0006_phase_7_budget_leak_anomalies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monthly_insight_reports",
        sa.Column("total_income", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "monthly_insight_reports",
        sa.Column("net_flow", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "monthly_insight_reports",
        sa.Column("transaction_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "monthly_insight_reports",
        sa.Column("generated_status", sa.String(length=50), nullable=False, server_default="complete"),
    )
    op.add_column(
        "monthly_insight_reports",
        sa.Column("generation_source", sa.String(length=50), nullable=False, server_default="deterministic"),
    )
    op.add_column(
        "monthly_insight_reports",
        sa.Column("safety_flags_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "monthly_insight_reports",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_check_constraint(
        "ck_monthly_insight_reports_transaction_count_nonnegative",
        "monthly_insight_reports",
        "transaction_count >= 0",
    )
    op.create_check_constraint(
        "ck_monthly_insight_reports_generated_status",
        "monthly_insight_reports",
        "generated_status IN ('complete', 'fallback')",
    )
    op.create_check_constraint(
        "ck_monthly_insight_reports_generation_source",
        "monthly_insight_reports",
        "generation_source IN ('deterministic', 'llm', 'llm_fallback')",
    )
    op.alter_column("monthly_insight_reports", "total_income", server_default=None)
    op.alter_column("monthly_insight_reports", "net_flow", server_default=None)
    op.alter_column("monthly_insight_reports", "transaction_count", server_default=None)
    op.alter_column("monthly_insight_reports", "generated_status", server_default=None)
    op.alter_column("monthly_insight_reports", "generation_source", server_default=None)
    op.alter_column("monthly_insight_reports", "safety_flags_json", server_default=None)
    op.alter_column("monthly_insight_reports", "updated_at", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_monthly_insight_reports_generation_source", "monthly_insight_reports", type_="check")
    op.drop_constraint("ck_monthly_insight_reports_generated_status", "monthly_insight_reports", type_="check")
    op.drop_constraint(
        "ck_monthly_insight_reports_transaction_count_nonnegative",
        "monthly_insight_reports",
        type_="check",
    )
    op.drop_column("monthly_insight_reports", "updated_at")
    op.drop_column("monthly_insight_reports", "safety_flags_json")
    op.drop_column("monthly_insight_reports", "generation_source")
    op.drop_column("monthly_insight_reports", "generated_status")
    op.drop_column("monthly_insight_reports", "transaction_count")
    op.drop_column("monthly_insight_reports", "net_flow")
    op.drop_column("monthly_insight_reports", "total_income")
