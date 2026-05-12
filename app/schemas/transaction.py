from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlmodel import SQLModel


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
    payment_type: str | None = None
    is_recurring_candidate: bool = False


class TransactionUpdate(SQLModel):
    merchant_normalized: str | None = None
    description: str | None = None
    category: str | None = None
    category_confidence: float | None = None
    payment_type: str | None = None
    is_recurring_candidate: bool | None = None


class TransactionRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    upload_id: uuid.UUID
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
