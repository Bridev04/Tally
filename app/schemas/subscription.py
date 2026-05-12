from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlmodel import SQLModel


class SubscriptionCreate(SQLModel):
    user_id: uuid.UUID
    merchant_name: str
    average_amount: Decimal
    frequency: str
    first_seen: date
    last_seen: date
    next_expected_date: date | None = None
    confidence_score: float = 0
    status: str = "active"


class SubscriptionUpdate(SQLModel):
    average_amount: Decimal | None = None
    frequency: str | None = None
    last_seen: date | None = None
    next_expected_date: date | None = None
    confidence_score: float | None = None
    status: str | None = None


class SubscriptionRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    merchant_name: str
    average_amount: Decimal
    frequency: str
    first_seen: date
    last_seen: date
    next_expected_date: date | None
    confidence_score: float
    status: str
    created_at: datetime
    updated_at: datetime
