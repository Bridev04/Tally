from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.routes.dashboard import get_dashboard_rate_limiter
from app.core.rate_limit import InMemoryRateLimiter
from app.models import SpendingAnomaly, Subscription, Transaction, TransactionUpload
from app.services.dashboard import DashboardService


def register_user(test_client: TestClient, email: str = "dashboard@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def seed_dashboard_data(session: Session, user_id: str, merchant_prefix: str = "") -> dict[str, list]:
    upload = TransactionUpload(
        user_id=UUID(user_id),
        file_name=f"{merchant_prefix or 'dashboard'}-seed.csv",
        upload_status="completed",
        total_rows=9,
        processed_rows=9,
    )
    session.add(upload)
    session.flush()
    rows = [
        (date(2026, 4, 20), "Old Month Store", "-999.00", "shopping", 0.95),
        (date(2026, 5, 6), "Company Payroll", "50000.00", "income", 1.0),
        (date(2026, 5, 10), "Netflix", "-549.00", "subscriptions", 0.92),
        (date(2026, 5, 11), "Grab", "-230.00", "transportation", 0.93),
        (date(2026, 5, 12), "Coffee Bar", "-150.00", "food", 0.90),
        (date(2026, 5, 13), "Canva", "-499.00", "subscriptions", 0.91),
        (date(2026, 5, 14), "Unknown Shop", "-88.00", "needs_review", 0.30),
        (date(2026, 5, 15), "Bakery", "-120.00", "food", 0.65),
        (date(2026, 6, 1), "Future Cafe", "-75.00", "food", 0.96),
    ]
    transactions = []
    for transaction_date, merchant, amount, category, confidence in rows:
        transaction = Transaction(
            user_id=UUID(user_id),
            upload_id=upload.id,
            transaction_date=transaction_date,
            merchant_raw=f"{merchant_prefix}{merchant}",
            merchant_normalized=f"{merchant_prefix}{merchant}".lower(),
            description="Imported demo row",
            amount=Decimal(amount),
            currency="PHP",
            category=category,
            category_confidence=confidence,
            category_source="auto",
        )
        session.add(transaction)
        transactions.append(transaction)

    subscriptions = [
        Subscription(
            user_id=UUID(user_id),
            merchant_name=f"{merchant_prefix}Netflix",
            average_amount=Decimal("549.00"),
            frequency="monthly",
            first_seen=date(2026, 3, 27),
            last_seen=date(2026, 5, 27),
            next_expected_date=date(2026, 6, 27),
            confidence_score=0.95,
            status="active",
        ),
        Subscription(
            user_id=UUID(user_id),
            merchant_name=f"{merchant_prefix}Spotify",
            average_amount=Decimal("149.00"),
            frequency="monthly",
            first_seen=date(2026, 3, 28),
            last_seen=date(2026, 5, 28),
            next_expected_date=date(2026, 6, 28),
            confidence_score=0.95,
            status="active",
        ),
        Subscription(
            user_id=UUID(user_id),
            merchant_name=f"{merchant_prefix}Paused App",
            average_amount=Decimal("99.00"),
            frequency="monthly",
            first_seen=date(2026, 3, 1),
            last_seen=date(2026, 5, 1),
            next_expected_date=date(2026, 6, 1),
            confidence_score=0.90,
            status="paused",
        ),
    ]
    session.add_all(subscriptions)

    anomalies = [
        SpendingAnomaly(
            user_id=UUID(user_id),
            anomaly_type="CATEGORY_SPIKE",
            category="food",
            merchant_name=None,
            amount_delta=Decimal("1240.00"),
            percentage_change=42.0,
            explanation="Food delivery increased by PHP 1,240 this month.",
            severity="high",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            created_at=datetime(2026, 5, 14, tzinfo=UTC),
        ),
        SpendingAnomaly(
            user_id=UUID(user_id),
            anomaly_type="NEEDS_REVIEW_CLUSTER",
            category="needs_review",
            merchant_name="Unknown Shop",
            amount_delta=Decimal("88.00"),
            percentage_change=None,
            explanation="A few imported rows may be worth reviewing.",
            severity="medium",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            created_at=datetime(2026, 5, 15, tzinfo=UTC),
        ),
        SpendingAnomaly(
            user_id=UUID(user_id),
            anomaly_type="MERCHANT_FREQUENCY_SPIKE",
            category="shopping",
            merchant_name="Old Month Store",
            amount_delta=Decimal("999.00"),
            percentage_change=30.0,
            explanation="Older month pattern.",
            severity="low",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            created_at=datetime(2026, 4, 30, tzinfo=UTC),
        ),
    ]
    session.add_all(anomalies)
    session.commit()
    return {"transactions": transactions, "subscriptions": subscriptions, "anomalies": anomalies}


def test_dashboard_service_returns_empty_state_for_new_user(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    summary = DashboardService().summarize(
        session=session,
        user_id=UUID(user["user"]["id"]),
        month=None,
        low_confidence_threshold=0.72,
    )

    assert summary.has_data is False
    assert summary.total_income == Decimal("0.00")
    assert summary.total_expenses == Decimal("0.00")
    assert summary.top_categories == []
    assert summary.recent_transactions == []
    assert summary.subscription_summary.active_count == 0
    assert summary.anomaly_summary.total_count == 0


def test_dashboard_service_summarizes_current_user_month_only(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client, "dashboard-owner@example.com")
    other = register_user(test_client, "dashboard-other@example.com")
    seed_dashboard_data(session, user["user"]["id"])
    seed_dashboard_data(session, other["user"]["id"], merchant_prefix="Other ")

    summary = DashboardService().summarize(
        session=session,
        user_id=UUID(user["user"]["id"]),
        month="2026-05",
        low_confidence_threshold=0.72,
    )

    assert summary.has_data is True
    assert summary.month == "2026-05"
    assert summary.total_income == Decimal("50000.00")
    assert summary.total_expenses == Decimal("1636.00")
    assert summary.net_flow == Decimal("48364.00")
    assert summary.transaction_count == 7
    assert summary.needs_review_count == 2
    assert [item.category for item in summary.top_categories] == ["subscriptions", "food", "transportation", "needs_review"]
    assert summary.top_categories[0].total_amount == Decimal("1048.00")
    assert len(summary.recent_transactions) == 5
    assert summary.recent_transactions[0].merchant_normalized == "bakery"
    assert summary.subscription_summary.active_count == 2
    assert summary.subscription_summary.estimated_monthly_total == Decimal("698.00")
    assert [item.merchant_name for item in summary.subscription_summary.upcoming_items] == ["Netflix", "Spotify"]
    assert summary.anomaly_summary.total_count == 2
    assert summary.anomaly_summary.high_count == 1
    assert summary.anomaly_summary.medium_count == 1
    assert summary.anomaly_summary.low_count == 0
    assert len(summary.anomaly_summary.latest_items) == 2
    assert summary.latest_upload is not None
    assert summary.latest_upload.file_name == "dashboard-seed.csv"


def test_dashboard_subscription_total_normalizes_frequency(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client, "dashboard-recurring-total@example.com")
    seed_dashboard_data(session, user["user"]["id"])
    subscriptions = [
        Subscription(
            user_id=UUID(user["user"]["id"]),
            merchant_name="Weekly Studio",
            average_amount=Decimal("120.00"),
            frequency="weekly",
            first_seen=date(2026, 3, 1),
            last_seen=date(2026, 5, 24),
            next_expected_date=date(2026, 5, 31),
            confidence_score=0.95,
            status="active",
        ),
        Subscription(
            user_id=UUID(user["user"]["id"]),
            merchant_name="Yearly Cloud",
            average_amount=Decimal("1200.00"),
            frequency="yearly",
            first_seen=date(2025, 5, 1),
            last_seen=date(2026, 5, 1),
            next_expected_date=date(2027, 5, 1),
            confidence_score=0.95,
            status="active",
        ),
    ]
    session.add_all(subscriptions)
    session.commit()

    summary = DashboardService().summarize(
        session=session,
        user_id=UUID(user["user"]["id"]),
        month="2026-05",
        low_confidence_threshold=0.72,
    )

    assert summary.subscription_summary.active_count == 4
    assert summary.subscription_summary.estimated_monthly_total == Decimal("1318.00")


def test_dashboard_default_month_uses_latest_transaction_month(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_dashboard_data(session, user["user"]["id"])

    summary = DashboardService().summarize(
        session=session,
        user_id=UUID(user["user"]["id"]),
        month=None,
        low_confidence_threshold=0.72,
    )
    may = DashboardService().summarize(
        session=session,
        user_id=UUID(user["user"]["id"]),
        month="2026-05",
        low_confidence_threshold=0.72,
    )

    assert summary.month == "2026-06"
    assert summary.transaction_count == 1
    assert may.transaction_count == 7


def test_dashboard_route_auth_validation_and_privacy(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client, "dashboard-route@example.com")
    other = register_user(test_client, "dashboard-route-other@example.com")
    seed_dashboard_data(session, user["user"]["id"])
    seed_dashboard_data(session, other["user"]["id"], merchant_prefix="Other ")

    unauthenticated = test_client.get("/dashboard/summary")
    invalid_month = test_client.get("/dashboard/summary?month=2026-99", headers=auth_headers(user))
    response = test_client.get("/dashboard/summary?month=2026-05", headers=auth_headers(user))

    assert unauthenticated.status_code == 401
    assert invalid_month.status_code == 422
    assert invalid_month.json() == {"detail": "Invalid request payload."}
    assert response.status_code == 200
    payload = response.json()
    payload_text = str(payload).lower()
    assert payload["has_data"] is True
    assert "password_hash" not in payload_text
    assert "raw" not in payload_text
    assert "other netflix" not in payload_text
    assert "dashboard-route-other" not in payload_text
    assert "traceback" not in payload_text
    assert "internal" not in payload_text


def test_dashboard_route_empty_state_for_authenticated_user(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.get("/dashboard/summary", headers=auth_headers(user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_data"] is False
    assert payload["total_income"] == "0.00"
    assert payload["subscription_summary"]["upcoming_items"] == []
    assert payload["anomaly_summary"]["latest_items"] == []


def test_dashboard_rate_limit_behavior(client) -> None:  # noqa: ANN001
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    client.dependency_overrides[get_dashboard_rate_limiter] = lambda: limiter
    test_client = TestClient(client)
    user = register_user(test_client, "dashboard-rate@example.com")

    first = test_client.get("/dashboard/summary", headers=auth_headers(user))
    second = test_client.get("/dashboard/summary", headers=auth_headers(user))

    assert first.status_code == 200
    assert second.status_code == 429
