from datetime import date
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, Numeric
from sqlmodel import Field, Relationship

from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction_upload import TransactionUpload
    from app.models.user import User


class Transaction(TimestampMixin, table=True):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "category_confidence IS NULL OR (category_confidence >= 0 AND category_confidence <= 1)",
            name="ck_transactions_category_confidence",
        ),
        CheckConstraint("length(currency) = 3", name="ck_transactions_currency_length"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    upload_id: uuid.UUID = Field(
        foreign_key="transaction_uploads.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    transaction_date: date = Field(nullable=False, index=True)
    merchant_raw: str = Field(nullable=False, max_length=500)
    merchant_normalized: str | None = Field(default=None, index=True, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    currency: str = Field(default="USD", nullable=False, max_length=3)
    category: str | None = Field(default=None, index=True, max_length=100)
    category_confidence: float | None = Field(default=None, ge=0, le=1)
    payment_type: str | None = Field(default=None, max_length=100)
    is_recurring_candidate: bool = Field(default=False, nullable=False)

    user: "User" = Relationship(back_populates="transactions")
    upload: "TransactionUpload" = Relationship(back_populates="transactions")
