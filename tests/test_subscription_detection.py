from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlmodel import Session

from app.models import Transaction, TransactionUpload, User
from app.services.subscription_detection import SubscriptionDetectionService


def seed_transactions(session: Session, user_id, rows: list[dict]) -> None:  # noqa: ANN001
    if session.get(User, user_id) is None:
        session.add(User(id=user_id, email=f"{user_id}@example.com", password_hash="test"))
        session.flush()
    upload = TransactionUpload(
        user_id=user_id,
        file_name="subscriptions.csv",
        upload_status="completed",
        total_rows=len(rows),
        processed_rows=len(rows),
    )
    session.add(upload)
    session.flush()
    for row in rows:
        session.add(
            Transaction(
                user_id=user_id,
                upload_id=upload.id,
                transaction_date=row["date"],
                merchant_raw=row["merchant"],
                merchant_normalized=row.get("merchant_normalized", row["merchant"].lower()),
                description=row.get("description", row["merchant"]),
                amount=Decimal(row["amount"]),
                currency="PHP",
                category=row.get("category"),
                category_source="auto",
            )
        )
    session.commit()


def test_detects_monthly_netflix_and_spotify(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 1, 1), "merchant": "Netflix", "amount": "-549", "category": "subscriptions"},
            {"date": date(2026, 2, 1), "merchant": "Netflix", "amount": "-549", "category": "subscriptions"},
            {"date": date(2026, 3, 1), "merchant": "Netflix", "amount": "-549", "category": "subscriptions"},
            {"date": date(2026, 4, 1), "merchant": "Netflix", "amount": "-549", "category": "subscriptions"},
            {"date": date(2026, 1, 5), "merchant": "Spotify", "amount": "-149", "category": "subscriptions"},
            {"date": date(2026, 2, 5), "merchant": "Spotify", "amount": "-149", "category": "subscriptions"},
            {"date": date(2026, 3, 5), "merchant": "Spotify", "amount": "-149", "category": "subscriptions"},
        ],
    )

    candidates = SubscriptionDetectionService().detect(session=session, user_id=user_id, as_of=date(2026, 4, 10))

    by_merchant = {candidate.merchant_key: candidate for candidate in candidates}
    assert by_merchant["netflix"].frequency == "monthly"
    assert by_merchant["netflix"].next_expected_date == date(2026, 5, 1)
    assert by_merchant["netflix"].confidence_score >= 0.90
    assert by_merchant["spotify"].frequency == "monthly"
    assert by_merchant["spotify"].confidence_score >= 0.85
    assert all(0 <= candidate.confidence_score <= 1 for candidate in candidates)


def test_detects_weekly_recurring_payment(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 1, 2), "merchant": "Weekly Studio", "amount": "-100", "category": "other"},
            {"date": date(2026, 1, 9), "merchant": "Weekly Studio", "amount": "-100", "category": "other"},
            {"date": date(2026, 1, 16), "merchant": "Weekly Studio", "amount": "-100", "category": "other"},
            {"date": date(2026, 1, 23), "merchant": "Weekly Studio", "amount": "-100", "category": "other"},
        ],
    )

    candidates = SubscriptionDetectionService().detect(session=session, user_id=user_id, as_of=date(2026, 1, 24))

    assert len(candidates) == 1
    assert candidates[0].frequency == "weekly"
    assert candidates[0].next_expected_date == date(2026, 1, 30)


def test_does_not_detect_random_grab_or_one_time_purchase(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 1, 3), "merchant": "Grab", "amount": "-230", "category": "transportation"},
            {"date": date(2026, 1, 18), "merchant": "Grab", "amount": "-180", "category": "transportation"},
            {"date": date(2026, 2, 8), "merchant": "Grab", "amount": "-420", "category": "transportation"},
            {"date": date(2026, 3, 22), "merchant": "Grab", "amount": "-135", "category": "transportation"},
            {"date": date(2026, 1, 4), "merchant": "Canva", "amount": "-299", "category": "subscriptions"},
        ],
    )

    candidates = SubscriptionDetectionService().detect(session=session, user_id=user_id, as_of=date(2026, 4, 1))

    assert candidates == []


def test_consistent_pattern_scores_higher_than_variable_pattern(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 1, 1), "merchant": "Consistent App", "amount": "-100", "category": "other"},
            {"date": date(2026, 2, 1), "merchant": "Consistent App", "amount": "-100", "category": "other"},
            {"date": date(2026, 3, 1), "merchant": "Consistent App", "amount": "-100", "category": "other"},
            {"date": date(2026, 4, 1), "merchant": "Consistent App", "amount": "-100", "category": "other"},
            {"date": date(2026, 1, 2), "merchant": "Variable App", "amount": "-98", "category": "other"},
            {"date": date(2026, 2, 2), "merchant": "Variable App", "amount": "-102", "category": "other"},
            {"date": date(2026, 3, 2), "merchant": "Variable App", "amount": "-99", "category": "other"},
            {"date": date(2026, 4, 2), "merchant": "Variable App", "amount": "-101", "category": "other"},
        ],
    )

    candidates = SubscriptionDetectionService().detect(session=session, user_id=user_id, as_of=date(2026, 4, 3))
    by_merchant = {candidate.merchant_key: candidate for candidate in candidates}

    assert by_merchant["consistent app"].confidence_score > by_merchant["variable app"].confidence_score


def test_handles_unknown_merchants_and_current_user_scope(session: Session) -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 1, 1), "merchant": "Mystery Service", "amount": "-200", "category": "other"},
            {"date": date(2026, 2, 1), "merchant": "Mystery Service", "amount": "-200", "category": "other"},
            {"date": date(2026, 3, 1), "merchant": "Mystery Service", "amount": "-200", "category": "other"},
        ],
    )
    seed_transactions(
        session,
        other_user_id,
        [
            {"date": date(2026, 1, 1), "merchant": "Other Service", "amount": "-200", "category": "subscriptions"},
            {"date": date(2026, 2, 1), "merchant": "Other Service", "amount": "-200", "category": "subscriptions"},
            {"date": date(2026, 3, 1), "merchant": "Other Service", "amount": "-200", "category": "subscriptions"},
        ],
    )

    candidates = SubscriptionDetectionService().detect(session=session, user_id=user_id, as_of=date(2026, 3, 3))

    assert [candidate.merchant_key for candidate in candidates] == ["mystery service"]


def test_repeated_detection_upserts_without_duplicates(session: Session) -> None:
    user_id = uuid4()
    seed_transactions(
        session,
        user_id,
        [
            {"date": date(2026, 1, 1), "merchant": "Netflix", "amount": "-549", "category": "subscriptions"},
            {"date": date(2026, 2, 1), "merchant": "Netflix", "amount": "-549", "category": "subscriptions"},
            {"date": date(2026, 3, 1), "merchant": "Netflix", "amount": "-549", "category": "subscriptions"},
        ],
    )
    service = SubscriptionDetectionService()

    first = service.detect_and_upsert(session=session, user_id=user_id, as_of=date(2026, 3, 2))
    second = service.detect_and_upsert(session=session, user_id=user_id, as_of=date(2026, 3, 2))

    assert first.detected_count == 1
    assert first.updated_count == 0
    assert second.detected_count == 1
    assert second.updated_count == 1
    assert first.subscriptions[0].id == second.subscriptions[0].id


def test_safe_behavior_with_no_transactions(session: Session) -> None:
    summary = SubscriptionDetectionService().detect_and_upsert(
        session=session,
        user_id=uuid4(),
        as_of=date(2026, 1, 1),
    )

    assert summary.detected_count == 0
    assert summary.subscriptions == []
