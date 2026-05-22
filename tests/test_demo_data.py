from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import MonthlyInsightReport, SpendingAnomaly, Subscription, Transaction, TransactionUpload
from app.services.demo_data import ALLOWED_DEMO_SCENARIOS, scenario_transactions
from tests.factories import create_transaction, create_upload


def register_user(test_client: TestClient, email: str = "demo@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def test_demo_scenarios_endpoint_returns_allowed_synthetic_scenarios(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.get("/demo/scenarios", headers=auth_headers(user))

    assert response.status_code == 200
    payload = response.json()
    assert [item["key"] for item in payload["scenarios"]] == list(ALLOWED_DEMO_SCENARIOS)
    assert "Full Portfolio Demo" in {item["title"] for item in payload["scenarios"]}
    assert "path" not in response.text.lower()


def test_loading_basic_demo_creates_marked_current_user_transactions(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "demo-one@example.com")
    second_user = register_user(test_client, "demo-two@example.com")

    response = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(first_user),
        json={"scenario": "basic", "run_processing": False},
    )

    assert response.status_code == 201
    assert response.json()["transactions_created"] == len(scenario_transactions["basic"])
    first_user_id = UUID(first_user["user"]["id"])
    second_user_id = UUID(second_user["user"]["id"])
    transactions = session.exec(select(Transaction).where(Transaction.user_id == first_user_id)).all()
    assert len(transactions) == len(scenario_transactions["basic"])
    assert {transaction.source for transaction in transactions} == {"demo"}
    assert {transaction.is_demo for transaction in transactions} == {True}
    assert {transaction.demo_scenario for transaction in transactions} == {"basic"}
    assert session.exec(select(Transaction).where(Transaction.user_id == second_user_id)).all() == []


def test_full_portfolio_demo_runs_processing_for_dashboard_reports_and_privacy(
    client,
    session: Session,
) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(user),
        json={"scenario": "full_portfolio", "reset_existing_demo": True, "run_processing": True},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["transactions_created"] >= 40
    assert payload["subscriptions_detected"] >= 4
    assert payload["anomalies_detected"] >= 4
    assert payload["reports_generated"] == 1

    dashboard = test_client.get("/dashboard/summary", headers=auth_headers(user))
    assert dashboard.status_code == 200
    assert dashboard.json()["has_data"] is True
    assert int(dashboard.json()["transaction_count"]) >= 30

    privacy = test_client.get("/settings/privacy/summary", headers=auth_headers(user))
    assert privacy.status_code == 200
    assert privacy.json()["has_demo_data"] is True
    assert privacy.json()["monthly_report_count"] == 1
    assert len(session.exec(select(MonthlyInsightReport)).all()) == 1


def test_subscription_and_budget_leak_scenarios_trigger_expected_processing(
    client,
    session: Session,
) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    subscription_user = register_user(test_client, "subscriptions@example.com")
    leak_user = register_user(test_client, "budget-leaks@example.com")

    subscriptions = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(subscription_user),
        json={"scenario": "subscriptions", "run_processing": True},
    )
    leaks = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(leak_user),
        json={"scenario": "budget_leaks", "run_processing": True},
    )

    assert subscriptions.status_code == 201
    assert subscriptions.json()["subscriptions_detected"] >= 4
    assert leaks.status_code == 201
    assert leaks.json()["anomalies_detected"] >= 4
    leak_user_id = UUID(leak_user["user"]["id"])
    anomaly_types = {
        item.anomaly_type
        for item in session.exec(select(SpendingAnomaly).where(SpendingAnomaly.user_id == leak_user_id)).all()
    }
    assert {
        "CATEGORY_SPIKE",
        "MERCHANT_FREQUENCY_SPIKE",
        "REPEATED_SMALL_PURCHASES",
        "DUPLICATE_LIKE_TRANSACTIONS",
    } <= anomaly_types


def test_needs_review_scenario_creates_low_confidence_items(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(user),
        json={"scenario": "needs_review", "run_processing": True},
    )

    assert response.status_code == 201
    transactions = session.exec(select(Transaction).where(Transaction.user_id == UUID(user["user"]["id"]))).all()
    assert len(transactions) == len(scenario_transactions["needs_review"])
    assert sum(1 for item in transactions if item.category == "needs_review") >= 5


def test_demo_reset_deletes_only_current_user_demo_records(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "reset-one@example.com")
    second_user = register_user(test_client, "reset-two@example.com")
    first_id = UUID(first_user["user"]["id"])
    second_id = UUID(second_user["user"]["id"])
    manual_upload = create_upload(session=session, user_id=first_id, file_name="manual-entry", source="manual")
    create_transaction(
        session=session,
        user_id=first_id,
        upload_id=manual_upload.id,
        merchant="Manual Keeper",
        source="manual",
    )

    assert test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(first_user),
        json={"scenario": "basic", "run_processing": False},
    ).status_code == 201
    assert test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(second_user),
        json={"scenario": "basic", "run_processing": False},
    ).status_code == 201

    response = test_client.post(
        "/demo/reset",
        headers=auth_headers(first_user),
        json={"scenario": "subscriptions", "run_processing": False},
    )

    assert response.status_code == 200
    first_transactions = session.exec(select(Transaction).where(Transaction.user_id == first_id)).all()
    second_transactions = session.exec(select(Transaction).where(Transaction.user_id == second_id)).all()
    assert any(item.merchant_raw == "Manual Keeper" and not item.is_demo for item in first_transactions)
    assert {item.demo_scenario for item in first_transactions if item.is_demo} == {"subscriptions"}
    assert {item.demo_scenario for item in second_transactions if item.is_demo} == {"basic"}


def test_duplicate_demo_loading_and_invalid_scenario_are_safe(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    first = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(user),
        json={"scenario": "basic", "run_processing": False},
    )
    second = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(user),
        json={"scenario": "basic", "run_processing": False},
    )
    invalid = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(user),
        json={"scenario": "real_bank_export"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["transactions_created"] == 0
    assert second.json()["duplicate_rows"] == len(scenario_transactions["basic"])
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "Invalid request payload."}
    assert "Traceback" not in invalid.text
    assert len(session.exec(select(Transaction)).all()) == len(scenario_transactions["basic"])


def test_clear_demo_data_uses_markers_and_preserves_non_demo_transactions(
    client,
    session: Session,
) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    user_id = UUID(user["user"]["id"])
    manual_upload = create_upload(session=session, user_id=user_id, file_name="manual-entry", source="manual")
    create_transaction(
        session=session,
        user_id=user_id,
        upload_id=manual_upload.id,
        merchant="Manual Keeper",
        source="manual",
    )

    assert test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(user),
        json={"scenario": "full_portfolio", "run_processing": True},
    ).status_code == 201

    response = test_client.post("/settings/privacy/clear-demo-data", headers=auth_headers(user))

    assert response.status_code == 200
    remaining = session.exec(select(Transaction).where(Transaction.user_id == user_id)).all()
    assert len(remaining) == 1
    assert remaining[0].merchant_raw == "Manual Keeper"
    demo_uploads = session.exec(
        select(TransactionUpload).where(
            TransactionUpload.user_id == user_id,
            TransactionUpload.is_demo.is_(True),
        )
    ).all()
    assert demo_uploads == []
    assert session.exec(select(Subscription).where(Subscription.user_id == user_id)).all() == []
