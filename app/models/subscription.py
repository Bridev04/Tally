from datetime import date
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, Numeric
from sqlmodel import Field, Relationship

from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Subscription(TimestampMixin, table=True):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("average_amount >= 0", name="ck_subscriptions_average_amount_nonnegative"),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_subscriptions_confidence_score",
        ),
        CheckConstraint("last_seen >= first_seen", name="ck_subscriptions_seen_date_order"),
        CheckConstraint(
            "status IN ('active', 'paused', 'cancelled')",
            name="ck_subscriptions_status",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    merchant_name: str = Field(nullable=False, index=True, max_length=255)
    average_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    frequency: str = Field(nullable=False, max_length=50)
    first_seen: date = Field(nullable=False)
    last_seen: date = Field(nullable=False)
    next_expected_date: date | None = Field(default=None)
    confidence_score: float = Field(default=0, nullable=False, ge=0, le=1)
    status: str = Field(default="active", nullable=False, max_length=50)

    user: "User" = Relationship(back_populates="subscriptions")
