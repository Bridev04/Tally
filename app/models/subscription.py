from datetime import date
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, Numeric
from sqlmodel import Field, Relationship

from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Subscription(TimestampMixin, table=True):
    __tablename__ = "subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    merchant_name: str = Field(nullable=False, index=True, max_length=255)
    average_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    frequency: str = Field(nullable=False, max_length=50)
    first_seen: date = Field(nullable=False)
    last_seen: date = Field(nullable=False)
    next_expected_date: date | None = Field(default=None)
    confidence_score: float = Field(default=0, nullable=False, ge=0, le=1)
    status: str = Field(default="active", nullable=False, max_length=50)

    user: "User" = Relationship(back_populates="subscriptions")
