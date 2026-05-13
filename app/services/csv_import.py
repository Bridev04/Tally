from dataclasses import dataclass, field
from io import StringIO
import csv
import uuid

from fastapi import UploadFile
from sqlmodel import Session

from app.models import TransactionUpload
from app.services.transaction_import_utils import (
    ImportValidationError,
    build_transaction,
    clean_text,
    create_upload_batch,
    find_duplicate_transaction,
    normalize_currency,
    normalize_merchant,
    parse_amount,
    parse_iso_date,
)


required_columns = {"date", "description", "merchant", "amount", "currency"}
allowed_csv_content_types = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}


@dataclass
class CSVImportResult:
    upload: TransactionUpload
    total_rows: int
    processed_rows: int
    duplicate_rows: int = 0
    invalid_rows: list[dict] = field(default_factory=list)


class CSVImportService:
    def __init__(self, *, max_upload_bytes: int, max_rows: int) -> None:
        self.max_upload_bytes = max_upload_bytes
        self.max_rows = max_rows

    async def import_upload(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        upload_file: UploadFile,
    ) -> CSVImportResult:
        self._validate_file_type(upload_file)
        upload = create_upload_batch(
            session=session,
            user_id=user_id,
            file_name=self._safe_file_name(upload_file.filename),
            status="pending",
        )
        upload.upload_status = "processing"

        try:
            contents = await upload_file.read()
            if len(contents) > self.max_upload_bytes:
                raise ImportValidationError("CSV file is too large.")
            rows = self._parse_rows(contents)
            if len(rows) > self.max_rows:
                raise ImportValidationError("CSV row limit exceeded.")

            processed_rows = 0
            duplicate_rows = 0
            for index, row in enumerate(rows, start=2):
                parsed = self._parse_csv_row(row)
                duplicate = find_duplicate_transaction(
                    session=session,
                    user_id=user_id,
                    transaction_date=parsed["transaction_date"],
                    merchant_normalized=parsed["merchant_normalized"],
                    amount=parsed["amount"],
                    description=parsed["description"],
                )
                if duplicate is not None:
                    duplicate_rows += 1
                    continue

                session.add(build_transaction(user_id=user_id, upload_id=upload.id, **parsed))
                processed_rows += 1

            upload.total_rows = len(rows)
            upload.processed_rows = processed_rows
            upload.upload_status = "completed"
            session.flush()
            return CSVImportResult(
                upload=upload,
                total_rows=len(rows),
                processed_rows=processed_rows,
                duplicate_rows=duplicate_rows,
            )
        except ImportValidationError as exc:
            upload.upload_status = "failed"
            upload.error_message = str(exc)
            session.flush()
            raise

    def _validate_file_type(self, upload_file: UploadFile) -> None:
        filename = self._safe_file_name(upload_file.filename)
        content_type = (upload_file.content_type or "").lower()
        if not filename.lower().endswith(".csv") or content_type not in allowed_csv_content_types:
            raise ImportValidationError("Upload must be a CSV file.")

    def _safe_file_name(self, filename: str | None) -> str:
        name = (filename or "transactions.csv").split("/")[-1].split("\\")[-1].strip()
        if not name:
            return "transactions.csv"
        return name[:255]

    def _parse_rows(self, contents: bytes) -> list[dict[str, str]]:
        try:
            text = contents.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportValidationError("CSV must be UTF-8 encoded.") from exc

        reader = csv.DictReader(StringIO(text))
        if reader.fieldnames is None:
            raise ImportValidationError("CSV is missing a header row.")
        fieldnames = {field.strip().lower() for field in reader.fieldnames}
        missing = required_columns - fieldnames
        if missing:
            raise ImportValidationError("CSV is missing required columns.")
        return list(reader)

    def _parse_csv_row(self, row: dict[str, str]) -> dict:
        transaction_date = parse_iso_date(row.get("date", ""))
        description = clean_text(row.get("description"), max_length=1000)
        merchant_raw = clean_text(row.get("merchant"), max_length=255)
        merchant_normalized = normalize_merchant(merchant_raw)
        if not merchant_normalized:
            raise ImportValidationError("Invalid merchant.")
        amount = parse_amount(row.get("amount", ""))
        currency = normalize_currency(row.get("currency", ""))
        return {
            "transaction_date": transaction_date,
            "merchant_raw": merchant_raw,
            "merchant_normalized": merchant_normalized,
            "description": description,
            "amount": amount,
            "currency": currency,
        }
