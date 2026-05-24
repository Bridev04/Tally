from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.transaction import TransactionCategory, TransactionRead


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChatExpenseParseRequest(StrictSchema):
    message: str = Field(min_length=1, max_length=500)
    timezone: str = Field(default="Asia/Manila", min_length=1, max_length=64)

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank.")
        return value


class ChatTransactionDraft(StrictSchema):
    transaction_type: Literal["expense", "income"]
    transaction_date: date
    merchant: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    currency: str = Field(default="PHP", min_length=3, max_length=3)
    category: TransactionCategory
    payment_type: str = Field(default="unknown", min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    source: Literal["ai_chat_manual"] = "ai_chat_manual"

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

    @field_validator("payment_type")
    @classmethod
    def normalize_payment_type(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_amount_sign(self) -> "ChatTransactionDraft":
        if self.transaction_type == "expense" and self.amount >= 0:
            raise ValueError("Expense amounts must be negative.")
        if self.transaction_type == "income" and self.amount <= 0:
            raise ValueError("Income amounts must be positive.")
        return self


class ChatExpenseParseResponse(BaseModel):
    reply: str
    clarification_needed: bool
    clarification_question: str | None = None
    draft: ChatTransactionDraft | None = None


class ChatExpenseConfirmRequest(StrictSchema):
    draft: ChatTransactionDraft


class ChatExpenseConfirmResponse(BaseModel):
    message: str
    transaction: TransactionRead
