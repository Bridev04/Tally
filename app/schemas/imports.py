from datetime import date, datetime
from decimal import Decimal
import uuid

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.transaction import TransactionCategory, TransactionRead


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ManualTransactionRequest(StrictSchema):
    transaction_date: date
    merchant: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    category: TransactionCategory | None = None

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


DemoScenario = Literal["basic", "subscriptions", "budget_leaks", "needs_review", "full_portfolio"]


class DemoLoadRequest(StrictSchema):
    scenario: DemoScenario = "full_portfolio"
    reset_existing_demo: bool = False
    run_processing: bool = True
    allow_overwrite: bool | None = None

    @property
    def should_reset_demo(self) -> bool:
        return self.reset_existing_demo or bool(self.allow_overwrite)


class DemoResetRequest(StrictSchema):
    scenario: DemoScenario | None = "full_portfolio"
    run_processing: bool = True


class DemoScenarioRead(BaseModel):
    key: DemoScenario
    title: str
    description: str


class DemoScenarioListResponse(BaseModel):
    scenarios: list[DemoScenarioRead]


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


class DemoLoadResponse(ImportResultResponse):
    scenario: DemoScenario
    transactions_created: int
    uploads_created: int
    subscriptions_detected: int
    anomalies_detected: int
    reports_generated: int
    reset_existing_demo: bool
    run_processing: bool
    message: str


class ManualTransactionResponse(BaseModel):
    transaction: TransactionRead


class TransactionListResponse(BaseModel):
    transactions: list[TransactionRead]
