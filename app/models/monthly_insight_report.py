from datetime import date
from datetime import datetime
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, JSON, Numeric
from sqlmodel import Field, Relationship, SQLModel

from app.models.common import utc_now

if TYPE_CHECKING:
    from app.models.user import User


class MonthlyInsightReport(SQLModel, table=True):
    __tablename__ = "monthly_insight_reports"
    __table_args__ = (
        CheckConstraint(
            "total_spend >= 0",
            name="ck_monthly_insight_reports_total_spend_nonnegative",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    month: date = Field(nullable=False, index=True)
    total_spend: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    total_income: Decimal = Field(default=Decimal("0.00"), sa_column=Column(Numeric(12, 2), nullable=False))
    net_flow: Decimal = Field(default=Decimal("0.00"), sa_column=Column(Numeric(12, 2), nullable=False))
    transaction_count: int = Field(default=0, nullable=False)
    top_categories_json: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    detected_subscriptions_json: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    anomalies_json: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    ai_summary: str | None = Field(default=None, max_length=4000)
    generated_status: str = Field(default="complete", nullable=False, max_length=50)
    generation_source: str = Field(default="deterministic", nullable=False, max_length=50)
    safety_flags_json: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    user: "User" = Relationship(back_populates="monthly_insight_reports")
