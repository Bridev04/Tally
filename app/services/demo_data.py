from datetime import date
from decimal import Decimal
import uuid

from sqlmodel import Session, select

from app.models import Transaction
from app.services.transaction_import_utils import (
    build_transaction,
    create_upload_batch,
    find_duplicate_transaction,
    normalize_merchant,
)


synthetic_transactions = [
    {
        "transaction_date": date(2026, 1, 1),
        "merchant_raw": "Netflix",
        "description": "Netflix Subscription",
        "amount": Decimal("-549.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 1, 3),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-230.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 1, 4),
        "merchant_raw": "Company Payroll",
        "description": "Salary",
        "amount": Decimal("35000.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 1, 7),
        "merchant_raw": "Meralco",
        "description": "Electric bill",
        "amount": Decimal("-3100.00"),
        "currency": "PHP",
    },
]


class DemoDataService:
    def load(self, *, session: Session, user_id: uuid.UUID, allow_overwrite: bool) -> tuple[object, int, int]:
        if allow_overwrite:
            existing = session.exec(select(Transaction).where(Transaction.user_id == user_id)).all()
            for transaction in existing:
                session.delete(transaction)
            session.flush()

        upload = create_upload_batch(
            session=session,
            user_id=user_id,
            file_name="synthetic-demo-data",
            total_rows=len(synthetic_transactions),
        )
        processed_rows = 0
        duplicate_rows = 0
        for item in synthetic_transactions:
            merchant_normalized = normalize_merchant(item["merchant_raw"])
            duplicate = find_duplicate_transaction(
                session=session,
                user_id=user_id,
                transaction_date=item["transaction_date"],
                merchant_normalized=merchant_normalized,
                amount=item["amount"],
                description=item["description"],
            )
            if duplicate is not None:
                duplicate_rows += 1
                continue
            session.add(
                build_transaction(
                    user_id=user_id,
                    upload_id=upload.id,
                    merchant_normalized=merchant_normalized,
                    **item,
                )
            )
            processed_rows += 1

        upload.processed_rows = processed_rows
        upload.upload_status = "completed"
        session.flush()
        return upload, processed_rows, duplicate_rows
