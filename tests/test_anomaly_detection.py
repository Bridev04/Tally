from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlmodel import Session

from app.models import Subscription, Transaction, TransactionUpload, User
from app.services.anomalies import AnomalyDetectionService


blocked_advice_words = ["cancel", "stop spending", "bad habit", "waste", "should"]


def seed_transactions(session: Session, user_id, rows: list[dict]) -> None:  # noqa: ANN001
    if session.get(User, user_id) is None:
        session.add(User(id=user_id, email=f"{user_id}@example.com", password_hash="test"))
        session.flush()
    upload = TransactionUpload(
        user_id=user_id,
        file_name="anomalies.csv",
        upload_status="completed",
        total_rows=len(rows),
        processed_rows=len(rows),
    )
    session.add(upload)
    session.flush()
    for row in rows:
        merchant = row["merchant"]
        session.add(
            Transaction(
                user_id=user_id,
                upload_id=upload.id,
                transaction_date=row["date"],
                merchant_raw=merchant,
                merchant_normalized=row.get("merchant_normalized", merchant.lower()),
                description=row.get("description", merchant),
                amount=Decimal(row["amount"]),
                currency="PHP",
                category=row.get("category", "other"),
                category_confidence=row.get("category_confidence", 0.95),
                category_source=row.get("category_source", "auto"),
            )
        )
    session.commit()


def test_detects_category_spike(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 4, 2), "merchant": "Cafe A", "amount": "-2500", "category": "food"},
            {"date": date(2026, 4, 15), "merchant": "Cafe B", "amount": "-2000", "category": "food"},
            {"date": date(2026, 5, 2), "merchant": "Cafe A", "amount": "-4000", "category": "food"},
            {"date": date(2026, 5, 18), "merchant": "Cafe C", "amount": "-4000", "category": "food"},
        ],
    )

    summary = AnomalyDetectionService().detect_and_upsert(session=session, user_id=user_id, month="2026-05")

    spike = next(item for item in summary.anomalies if item.anomaly_type == "CATEGORY_SPIKE")
    assert spike.category == "food"
    assert spike.amount_delta == Decimal("3500.00")
    assert spike.percentage_change == 77.8
    assert spike.severity == "medium"


def test_does_not_detect_category_spike_below_threshold(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 4, 2), "merchant": "Cafe A", "amount": "-1000", "category": "food"},
            {"date": date(2026, 5, 2), "merchant": "Cafe A", "amount": "-1300", "category": "food"},
        ],
    )

    summary = AnomalyDetectionService().detect_and_upsert(session=session, user_id=user_id, month="2026-05")

    assert all(item.anomaly_type != "CATEGORY_SPIKE" for item in summary.anomalies)


def test_detects_merchant_frequency_spike(session: Session) -> None:
    user_id = uuid4()
    rows = [{"date": date(2026, 4, day), "merchant": "Grab", "amount": "-120", "category": "transportation"} for day in range(1, 6)]
    rows.extend(
        {"date": date(2026, 5, day), "merchant": "Grab", "amount": "-120", "category": "transportation"}
        for day in range(1, 15)
    )
    seed_transactions(session, user_id, rows)

    summary = AnomalyDetectionService().detect_and_upsert(session=session, user_id=user_id, month="2026-05")

    anomaly = next(item for item in summary.anomalies if item.anomaly_type == "MERCHANT_FREQUENCY_SPIKE")
    assert anomaly.merchant_name == "Grab"
    assert anomaly.transaction_count == 14


def test_detects_repeated_small_purchases(session: Session) -> None:
    user_id = uuid4()
    rows = [
        {"date": date(2026, 5, day), "merchant": "Starbucks", "amount": "-180", "category": "food"}
        for day in range(1, 8)
    ]
    seed_transactions(session, user_id, rows)

    summary = AnomalyDetectionService().detect_and_upsert(session=session, user_id=user_id, month="2026-05")

    anomaly = next(item for item in summary.anomalies if item.anomaly_type == "REPEATED_SMALL_PURCHASES")
    assert anomaly.amount_delta == Decimal("1260.00")
    assert "Small purchases at Starbucks" in anomaly.explanation


def test_detects_duplicate_like_transactions(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 5, 3), "merchant": "Netflix", "description": "Netflix", "amount": "-549", "category": "subscriptions"},
            {"date": date(2026, 5, 3), "merchant": "Netflix", "description": "Netflix", "amount": "-549", "category": "subscriptions"},
        ],
    )

    summary = AnomalyDetectionService().detect_and_upsert(session=session, user_id=user_id, month="2026-05")

    anomaly = next(item for item in summary.anomalies if item.anomaly_type == "DUPLICATE_LIKE_TRANSACTIONS")
    assert anomaly.transaction_count == 2
    assert "description" not in anomaly.explanation.lower()


def test_detects_needs_review_cluster(session: Session) -> None:
    user_id = uuid4()
    rows = [
        {
            "date": date(2026, 5, day),
            "merchant": f"Unknown {day}",
            "amount": "-100",
            "category": "needs_review",
            "category_confidence": 0.30,
        }
        for day in range(1, 6)
    ]
    seed_transactions(session, user_id, rows)

    summary = AnomalyDetectionService().detect_and_upsert(session=session, user_id=user_id, month="2026-05")

    anomaly = next(item for item in summary.anomalies if item.anomaly_type == "NEEDS_REVIEW_CLUSTER")
    assert anomaly.severity == "low"
    assert anomaly.transaction_count == 5


def test_detects_subscription_price_change(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [{"date": date(2026, 5, 5), "merchant": "Spotify", "amount": "-179", "category": "subscriptions"}],
    )
    session.add(
        Subscription(
            user_id=user_id,
            merchant_name="Spotify",
            average_amount=Decimal("149.00"),
            frequency="monthly",
            first_seen=date(2026, 1, 5),
            last_seen=date(2026, 4, 5),
            confidence_score=0.95,
            status="active",
        )
    )
    session.commit()

    summary = AnomalyDetectionService().detect_and_upsert(session=session, user_id=user_id, month="2026-05")

    anomaly = next(item for item in summary.anomalies if item.anomaly_type == "SUBSCRIPTION_PRICE_CHANGE")
    assert anomaly.amount_delta == Decimal("30.00")
    assert anomaly.percentage_change == 20.1


def test_severity_calculation_and_neutral_explanations(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 4, 1), "merchant": "Store", "amount": "-2500", "category": "shopping"},
            {"date": date(2026, 5, 1), "merchant": "Store", "amount": "-6000", "category": "shopping"},
        ],
    )

    summary = AnomalyDetectionService().detect_and_upsert(session=session, user_id=user_id, month="2026-05")

    anomaly = next(item for item in summary.anomalies if item.anomaly_type == "CATEGORY_SPIKE")
    assert anomaly.severity == "high"
    explanations = " ".join(item.explanation.lower() for item in summary.anomalies)
    assert all(word not in explanations for word in blocked_advice_words)
