from datetime import date, datetime
from decimal import Decimal
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ManualTransactionRequest(StrictSchema):
    transaction_date: date
    merchant: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    category: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("amount")
    @classmethod
    def amount_must_be_nonzero(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value == 0:
            raise ValueError("Amount must be a non-zero number.")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("Currency must be a three-letter code.")
        return normalized


class PastePreviewRequest(StrictSchema):
    text: str = Field(min_length=1)


class PasteConfirmRequest(PastePreviewRequest):
    pass


class DemoLoadRequest(StrictSchema):
    allow_overwrite: bool = False


class TransactionRead(BaseModel):
    id: uuid.UUID
    transaction_date: date
    merchant_raw: str
    merchant_normalized: str | None
    description: str | None
    amount: Decimal
    currency: str
    category: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadRead(BaseModel):
    id: uuid.UUID
    file_name: str
    upload_status: str
    total_rows: int
    processed_rows: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportErrorRow(BaseModel):
    row_number: int
    reason: str


class PasteValidRow(BaseModel):
    row_number: int
    transaction_date: date
    merchant: str
    merchant_normalized: str
    description: str
    amount: Decimal
    currency: str


class PastePreviewResponse(BaseModel):
    valid_rows: list[PasteValidRow]
    invalid_rows: list[ImportErrorRow]


class ImportResultResponse(BaseModel):
    upload_id: uuid.UUID
    total_rows: int
    processed_rows: int
    duplicate_rows: int
    invalid_rows: list[ImportErrorRow] = []


class ManualTransactionResponse(BaseModel):
    transaction: TransactionRead


class TransactionListResponse(BaseModel):
    transactions: list[TransactionRead]
