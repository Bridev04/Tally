import uuid

from fastapi import HTTPException, status
from sqlmodel import Session

from app.models import Transaction
from app.schemas.imports import ManualTransactionRequest
from app.services.transaction_import_utils import (
    build_transaction,
    clean_text,
    create_upload_batch,
    find_duplicate_transaction,
    normalize_merchant,
    parse_amount,
)


class ManualTransactionService:
    def create(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        payload: ManualTransactionRequest,
    ) -> Transaction:
        merchant_raw = clean_text(payload.merchant, max_length=255)
        description = clean_text(payload.description, max_length=1000)
        merchant_normalized = normalize_merchant(merchant_raw)
        amount = parse_amount(payload.amount)
        duplicate = find_duplicate_transaction(
            session=session,
            user_id=user_id,
            transaction_date=payload.transaction_date,
            merchant_normalized=merchant_normalized,
            amount=amount,
            description=description,
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction already exists.",
            )

        upload = create_upload_batch(
            session=session,
            user_id=user_id,
            file_name="manual-entry",
            total_rows=1,
        )
        transaction = build_transaction(
            user_id=user_id,
            upload_id=upload.id,
            transaction_date=payload.transaction_date,
            merchant_raw=merchant_raw,
            merchant_normalized=merchant_normalized,
            description=description,
            amount=amount,
            currency=payload.currency,
            category=payload.category.value if payload.category is not None else None,
            category_source="manual" if payload.category is not None else None,
        )
        session.add(transaction)
        upload.processed_rows = 1
        upload.upload_status = "completed"
        session.flush()
        return transaction
