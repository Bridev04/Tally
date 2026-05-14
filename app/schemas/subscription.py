from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import SQLModel

from app.schemas.transaction import StrictSchema


class SubscriptionStatus(StrEnum):
    active = "active"
    paused = "paused"
    cancelled = "cancelled"


class SubscriptionFrequency(StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    yearly = "yearly"


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


class SubscriptionRead(BaseModel):
    id: uuid.UUID
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

    model_config = ConfigDict(from_attributes=True)


class SubscriptionListResponse(BaseModel):
    subscriptions: list[SubscriptionRead]
    limit: int
    offset: int
    count: int


class SubscriptionDetectionResponse(BaseModel):
    subscriptions: list[SubscriptionRead]
    detected_count: int
    updated_count: int


class SubscriptionStatusUpdate(StrictSchema):
    status: SubscriptionStatus


class SubscriptionFilterParams(BaseModel):
    status: SubscriptionStatus | None = None
    frequency: SubscriptionFrequency | None = None
    search: str | None = Field(default=None, min_length=1, max_length=255)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("search")
    @classmethod
    def reject_blank_search(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Value cannot be blank.")
        return value
