from datetime import date, datetime
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, JSON, Numeric
from sqlmodel import Field, Relationship, SQLModel

from app.models.common import utc_now

if TYPE_CHECKING:
    from app.models.user import User


class SpendingAnomaly(SQLModel, table=True):
    __tablename__ = "spending_anomalies"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_spending_anomalies_severity",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    anomaly_type: str = Field(nullable=False, max_length=100)
    category: str | None = Field(default=None, index=True, max_length=100)
    merchant_name: str | None = Field(default=None, index=True, max_length=255)
    amount_delta: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 2)))
    percentage_change: float | None = Field(default=None)
    explanation: str = Field(nullable=False, max_length=2000)
    severity: str = Field(default="medium", nullable=False, max_length=50)
    period_start: date | None = Field(default=None, index=True)
    period_end: date | None = Field(default=None, index=True)
    baseline_period_start: date | None = Field(default=None)
    baseline_period_end: date | None = Field(default=None)
    transaction_count: int | None = Field(default=None)
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    user: "User" = Relationship(back_populates="spending_anomalies")
