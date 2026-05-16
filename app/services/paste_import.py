from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import re
import uuid

from sqlmodel import Session

from app.models import TransactionUpload
from app.services.transaction_import_utils import (
    ImportValidationError,
    build_transaction,
    create_upload_batch,
    find_duplicate_transaction,
    normalize_currency,
    normalize_merchant,
    parse_amount,
    parse_iso_date,
)


month_numbers = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
amount_pattern = re.compile(r"^-?\d+(?:,\d{3})*(?:\.\d{1,2})?$|^-?\d+(?:\.\d{1,2})?$")


@dataclass
class ParsedPasteRow:
    row_number: int
    transaction_date: date
    merchant: str
    merchant_normalized: str
    description: str
    amount: Decimal
    currency: str


@dataclass
class PastePreview:
    valid_rows: list[ParsedPasteRow] = field(default_factory=list)
    invalid_rows: list[dict] = field(default_factory=list)


@dataclass
class PasteImportResult:
    upload: TransactionUpload
    total_rows: int
    processed_rows: int
    duplicate_rows: int
    invalid_rows: list[dict]


class PasteImportService:
    def __init__(self, *, max_rows: int, max_bytes: int) -> None:
        self.max_rows = max_rows
        self.max_bytes = max_bytes

    def preview(self, *, text: str) -> PastePreview:
        lines = self._safe_lines(text)
        preview = PastePreview()
        for row_number, line in lines:
            try:
                preview.valid_rows.append(self._parse_line(row_number=row_number, line=line))
            except ImportValidationError as exc:
                preview.invalid_rows.append({"row_number": row_number, "reason": str(exc)})
        return preview

    def confirm(self, *, session: Session, user_id: uuid.UUID, text: str) -> PasteImportResult:
        preview = self.preview(text=text)
        upload = create_upload_batch(
            session=session,
            user_id=user_id,
            file_name="paste-import",
            total_rows=len(preview.valid_rows) + len(preview.invalid_rows),
        )
        processed_rows = 0
        duplicate_rows = 0
        for row in preview.valid_rows:
            duplicate = find_duplicate_transaction(
                session=session,
                user_id=user_id,
                transaction_date=row.transaction_date,
                merchant_normalized=row.merchant_normalized,
                amount=row.amount,
                description=row.description,
            )
            if duplicate is not None:
                duplicate_rows += 1
                continue
            session.add(
                build_transaction(
                    user_id=user_id,
                    upload_id=upload.id,
                    transaction_date=row.transaction_date,
                    merchant_raw=row.merchant,
                    merchant_normalized=row.merchant_normalized,
                    description=row.description,
                    amount=row.amount,
                    currency=row.currency,
                )
            )
            processed_rows += 1

        upload.processed_rows = processed_rows
        upload.upload_status = "completed"
        session.flush()
        return PasteImportResult(
            upload=upload,
            total_rows=upload.total_rows,
            processed_rows=processed_rows,
            duplicate_rows=duplicate_rows,
            invalid_rows=preview.invalid_rows,
        )

    def _safe_lines(self, text: str) -> list[tuple[int, str]]:
        if len(text.encode("utf-8")) > self.max_bytes:
            raise ImportValidationError("Pasted input is too large.")
        lines = [(index, line.strip()) for index, line in enumerate(text.splitlines(), start=1) if line.strip()]
        if len(lines) > self.max_rows:
            raise ImportValidationError("Too many pasted rows.")
        return lines

    def _parse_line(self, *, row_number: int, line: str) -> ParsedPasteRow:
        tokens = line.split()
        if len(tokens) < 4:
            raise ImportValidationError("Row is missing required values.")
        currency = normalize_currency(tokens[-1])
        if not amount_pattern.match(tokens[-2]):
            raise ImportValidationError("Invalid amount.")
        amount = parse_amount(tokens[-2])

        if re.match(r"^\d{4}-\d{2}-\d{2}$", tokens[0]):
            transaction_date = parse_iso_date(tokens[0])
            text_tokens = tokens[1:-2]
        else:
            if len(tokens) < 5:
                raise ImportValidationError("Row is missing required values.")
            month = month_numbers.get(tokens[0].lower().rstrip("."))
            if month is None:
                raise ImportValidationError("Invalid date.")
            day_text = tokens[1].rstrip(",")
            if not day_text.isdigit():
                raise ImportValidationError("Invalid date.")
            try:
                transaction_date = date(date.today().year, month, int(day_text))
            except ValueError as exc:
                raise ImportValidationError("Invalid date.") from exc
            text_tokens = tokens[2:-2]

        if not text_tokens:
            raise ImportValidationError("Missing merchant.")
        description = " ".join(text_tokens)
        merchant = text_tokens[-1]
        merchant_normalized = normalize_merchant(merchant)
        if not merchant_normalized:
            raise ImportValidationError("Invalid merchant.")
        return ParsedPasteRow(
            row_number=row_number,
            transaction_date=transaction_date,
            merchant=merchant,
            merchant_normalized=merchant_normalized,
            description=description,
            amount=amount,
            currency=currency,
        )
