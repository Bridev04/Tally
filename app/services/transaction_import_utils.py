from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import uuid

from sqlmodel import Session, select

from app.models import Transaction, TransactionUpload


class ImportValidationError(ValueError):
    pass


whitespace_pattern = re.compile(r"\s+")
merchant_noise_pattern = re.compile(r"[^a-z0-9 ]+")


def normalize_merchant(value: str) -> str:
    cleaned = merchant_noise_pattern.sub(" ", value.lower().strip())
    return whitespace_pattern.sub(" ", cleaned).strip()


def clean_text(value: str | None, *, max_length: int) -> str:
    if value is None:
        return ""
    cleaned = whitespace_pattern.sub(" ", value.strip())
    if not cleaned:
        raise ImportValidationError("Missing required text value.")
    if len(cleaned) > max_length:
        raise ImportValidationError("Text value is too long.")
    return cleaned


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ImportValidationError("Invalid date.") from exc


def parse_amount(value: str | Decimal) -> Decimal:
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ImportValidationError("Invalid amount.") from exc
    if not amount.is_finite() or amount == 0:
        raise ImportValidationError("Invalid amount.")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def normalize_currency(value: str) -> str:
    currency = value.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ImportValidationError("Invalid currency.")
    return currency


def find_duplicate_transaction(
    *,
    session: Session,
    user_id: uuid.UUID,
    transaction_date: date,
    merchant_normalized: str,
    amount: Decimal,
    description: str,
) -> Transaction | None:
    return session.exec(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date == transaction_date,
            Transaction.merchant_normalized == merchant_normalized,
            Transaction.amount == amount,
            Transaction.description == description,
        )
    ).first()


def create_upload_batch(
    *,
    session: Session,
    user_id: uuid.UUID,
    file_name: str,
    total_rows: int = 0,
    status: str = "processing",
) -> TransactionUpload:
    upload = TransactionUpload(
        user_id=user_id,
        file_name=file_name,
        upload_status=status,
        total_rows=total_rows,
        processed_rows=0,
    )
    session.add(upload)
    session.flush()
    return upload


def build_transaction(
    *,
    user_id: uuid.UUID,
    upload_id: uuid.UUID,
    transaction_date: date,
    merchant_raw: str,
    merchant_normalized: str,
    description: str,
    amount: Decimal,
    currency: str,
    category: str | None = None,
) -> Transaction:
    return Transaction(
        user_id=user_id,
        upload_id=upload_id,
        transaction_date=transaction_date,
        merchant_raw=merchant_raw,
        merchant_normalized=merchant_normalized,
        description=description,
        amount=amount,
        currency=currency,
        category=category,
    )
