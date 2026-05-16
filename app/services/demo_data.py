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
        "transaction_date": date(2026, 2, 1),
        "merchant_raw": "Netflix",
        "description": "Netflix Subscription",
        "amount": Decimal("-549.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 3, 1),
        "merchant_raw": "Netflix",
        "description": "Netflix Subscription",
        "amount": Decimal("-549.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 4, 1),
        "merchant_raw": "Netflix",
        "description": "Netflix Subscription",
        "amount": Decimal("-549.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 5, 1),
        "merchant_raw": "Netflix",
        "description": "Netflix Subscription",
        "amount": Decimal("-549.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 1, 5),
        "merchant_raw": "Spotify",
        "description": "Spotify Premium",
        "amount": Decimal("-149.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 2, 5),
        "merchant_raw": "Spotify",
        "description": "Spotify Premium",
        "amount": Decimal("-149.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 3, 5),
        "merchant_raw": "Spotify",
        "description": "Spotify Premium",
        "amount": Decimal("-149.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 4, 5),
        "merchant_raw": "Spotify",
        "description": "Spotify Premium",
        "amount": Decimal("-149.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 5, 5),
        "merchant_raw": "Spotify",
        "description": "Spotify Premium",
        "amount": Decimal("-149.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 5, 25),
        "merchant_raw": "Spotify",
        "description": "Spotify Premium",
        "amount": Decimal("-179.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 1, 10),
        "merchant_raw": "iCloud",
        "description": "iCloud storage",
        "amount": Decimal("-49.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 2, 10),
        "merchant_raw": "iCloud",
        "description": "iCloud storage",
        "amount": Decimal("-49.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 3, 10),
        "merchant_raw": "iCloud",
        "description": "iCloud storage",
        "amount": Decimal("-49.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 4, 10),
        "merchant_raw": "iCloud",
        "description": "iCloud storage",
        "amount": Decimal("-49.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 5, 10),
        "merchant_raw": "iCloud",
        "description": "iCloud storage",
        "amount": Decimal("-49.00"),
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
        "transaction_date": date(2026, 1, 18),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-180.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 2, 8),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-420.00"),
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
    {
        "transaction_date": date(2026, 2, 14),
        "merchant_raw": "Coffee Bar",
        "description": "Coffee and pastry",
        "amount": Decimal("-285.00"),
        "currency": "PHP",
    },
    {
        "transaction_date": date(2026, 4, 3),
        "merchant_raw": "Supermart",
        "description": "Groceries",
        "amount": Decimal("-2200.00"),
        "currency": "PHP",
        "category": "food",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 4, 17),
        "merchant_raw": "Neighborhood Cafe",
        "description": "Meals",
        "amount": Decimal("-2300.00"),
        "currency": "PHP",
        "category": "food",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 12),
        "merchant_raw": "Supermart",
        "description": "Groceries",
        "amount": Decimal("-4300.00"),
        "currency": "PHP",
        "category": "food",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 19),
        "merchant_raw": "Neighborhood Cafe",
        "description": "Meals",
        "amount": Decimal("-3900.00"),
        "currency": "PHP",
        "category": "food",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 4, 2),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-160.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 4, 6),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-180.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 4, 11),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-140.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 4, 18),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-190.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 4, 27),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-175.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 2),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-170.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 4),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-155.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 6),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-185.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 8),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-165.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 10),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-145.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 12),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-205.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 14),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-175.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 16),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-195.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 18),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-160.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 20),
        "merchant_raw": "Grab",
        "description": "Grab Ride",
        "amount": Decimal("-180.00"),
        "currency": "PHP",
        "category": "transportation",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 3),
        "merchant_raw": "Netflix",
        "description": "Netflix charge",
        "amount": Decimal("-549.00"),
        "currency": "PHP",
        "category": "subscriptions",
        "category_source": "imported",
    },
    {
        "transaction_date": date(2026, 5, 3),
        "merchant_raw": "Netflix",
        "description": "netflix charge",
        "amount": Decimal("-549.00"),
        "currency": "PHP",
        "category": "subscriptions",
        "category_source": "imported",
    },
    *[
        {
            "transaction_date": date(2026, 5, day),
            "merchant_raw": "Daily Brew",
            "description": "Coffee",
            "amount": Decimal("-180.00"),
            "currency": "PHP",
            "category": "food",
            "category_source": "imported",
        }
        for day in range(21, 28)
    ],
    *[
        {
            "transaction_date": date(2026, 5, day),
            "merchant_raw": f"Unmapped Merchant {day}",
            "description": "Imported row needs review",
            "amount": Decimal("-95.00"),
            "currency": "PHP",
            "category": "needs_review",
            "category_source": "imported",
        }
        for day in range(1, 6)
    ],
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
