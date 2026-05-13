from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import SQLModel


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TransactionCategory(StrEnum):
    food = "food"
    transportation = "transportation"
    rent = "rent"
    subscriptions = "subscriptions"
    shopping = "shopping"
    entertainment = "entertainment"
    utilities = "utilities"
    education = "education"
    health = "health"
    income = "income"
    transfer = "transfer"
    fees = "fees"
    other = "other"
    needs_review = "needs_review"


class TransactionCreate(SQLModel):
    user_id: uuid.UUID
    upload_id: uuid.UUID
    transaction_date: date
    merchant_raw: str
    merchant_normalized: str | None = None
    description: str | None = None
    amount: Decimal
    currency: str = "USD"
    category: str | None = None
    category_confidence: float | None = None
    category_manually_set: bool = False
    payment_type: str | None = None
    is_recurring_candidate: bool = False


class TransactionUpdate(SQLModel):
    merchant_normalized: str | None = None
    description: str | None = None
    category: str | None = None
    category_confidence: float | None = None
    category_manually_set: bool | None = None
    payment_type: str | None = None
    is_recurring_candidate: bool | None = None


class TransactionRead(BaseModel):
    id: uuid.UUID
    transaction_date: date
    merchant_raw: str
    merchant_normalized: str | None
    description: str | None
    amount: Decimal
    currency: str
    category: str | None
    category_confidence: float | None
    payment_type: str | None
    is_recurring_candidate: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    transactions: list[TransactionRead]
    limit: int
    offset: int
    count: int


class TransactionFilterParams(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    category: TransactionCategory | None = None
    merchant: str | None = Field(default=None, min_length=1, max_length=255)
    search: str | None = Field(default=None, min_length=1, max_length=255)
    payment_type: str | None = Field(default=None, min_length=1, max_length=100)
    min_amount: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    max_amount: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("merchant", "search", "payment_type")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Value cannot be blank.")
        return value

    @field_validator("max_amount")
    @classmethod
    def validate_amount_range(cls, value: Decimal | None, info) -> Decimal | None:  # noqa: ANN001
        min_amount = info.data.get("min_amount")
        if value is not None and min_amount is not None and value < min_amount:
            raise ValueError("max_amount must be greater than or equal to min_amount.")
        return value

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, value: date | None, info) -> date | None:  # noqa: ANN001
        date_from = info.data.get("date_from")
        if value is not None and date_from is not None and value < date_from:
            raise ValueError("date_to must be on or after date_from.")
        return value


class TransactionCategoryUpdate(StrictSchema):
    category: TransactionCategory


class CategorySummaryItem(BaseModel):
    category: str
    total_amount: Decimal
    transaction_count: int
    percentage_of_total_expenses: Decimal


class CategorySummaryResponse(BaseModel):
    items: list[CategorySummaryItem]
    total_expenses: Decimal
    total_income: Decimal
    transaction_count: int


class MerchantSummaryItem(BaseModel):
    merchant_normalized: str
    total_amount: Decimal
    transaction_count: int
    first_seen: date
    last_seen: date


class MerchantSummaryResponse(BaseModel):
    items: list[MerchantSummaryItem]
