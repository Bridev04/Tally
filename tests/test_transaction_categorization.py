from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import AuditLog, Transaction, TransactionUpload
from app.services.transaction_categorizer import TransactionCategorizerService


def register_user(test_client: TestClient, email: str = "categorizer@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def seed_upload(session: Session, user_id: str) -> TransactionUpload:
    upload = TransactionUpload(
        user_id=UUID(user_id),
        file_name="categorization.csv",
        upload_status="completed",
        total_rows=0,
        processed_rows=0,
    )
    session.add(upload)
    session.flush()
    return upload


def add_transaction(
    session: Session,
    *,
    user_id: str,
    upload_id,
    merchant: str,
    description: str,
    category: str | None = None,
    category_source: str = "unknown",
    manual: bool = False,
) -> Transaction:
    transaction = Transaction(
        user_id=UUID(user_id),
        upload_id=upload_id,
        transaction_date=date(2026, 1, 10),
        merchant_raw=merchant,
        merchant_normalized=TransactionCategorizerService.normalize_merchant(merchant),
        description=description,
        amount=Decimal("-100.00"),
        currency="PHP",
        category=category,
        category_source=category_source,
        category_manually_set=manual,
    )
    session.add(transaction)
    session.flush()
    return transaction


def test_deterministic_category_rules() -> None:
    service = TransactionCategorizerService()

    examples = {
        "Netflix": "subscriptions",
        "Spotify Pte Ltd": "subscriptions",
        "PAYPAL *CANVA": "subscriptions",
        "Grab": "transportation",
        "Uber": "transportation",
        "Jollibee": "food",
        "Starbucks": "food",
    }
    for merchant, category in examples.items():
        result = service.categorize_values(merchant_raw=merchant, description="")
        assert result.category == category
        assert 0 <= result.confidence <= 1

    assert service.categorize_values(merchant_raw="Company", description="salary payroll").category == "income"
    assert service.categorize_values(merchant_raw="Bank", description="service charge").category == "fees"
    unknown = service.categorize_values(merchant_raw="Mystery Store 9981", description="unknown purchase")
    assert unknown.category == "needs_review"
    assert unknown.confidence < 0.50


def test_merchant_normalization_examples() -> None:
    service = TransactionCategorizerService()

    assert service.normalize_merchant("NETFLIX.COM") == "netflix"
    assert service.normalize_merchant("GRAB*TRIP") == "grab"
    assert service.normalize_merchant("McDonald's") == "mcdonalds"
    assert service.normalize_merchant("MCDO") == "mcdonalds"
    assert service.normalize_merchant("PAYPAL *CANVA") == "canva"


def test_confidence_scoring_is_explainable_and_bounded() -> None:
    service = TransactionCategorizerService()

    exact = service.categorize_values(merchant_raw="Netflix", description="")
    description_only = service.categorize_values(merchant_raw="Unknown Store", description="Netflix subscription")
    unknown = service.categorize_values(merchant_raw="Unknown Store", description="Reference 123")

    assert exact.confidence >= 0.80
    assert description_only.confidence < exact.confidence
    assert unknown.confidence < 0.50
    for result in (exact, description_only, unknown):
        assert 0 <= result.confidence <= 1
        assert result.reason


def test_categorize_route_preserves_manual_categories(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    upload = seed_upload(session, user["user"]["id"])
    auto = add_transaction(
        session,
        user_id=user["user"]["id"],
        upload_id=upload.id,
        merchant="Netflix",
        description="Netflix subscription",
    )
    manual = add_transaction(
        session,
        user_id=user["user"]["id"],
        upload_id=upload.id,
        merchant="Grab",
        description="Grab ride",
        category="food",
        category_source="manual",
        manual=True,
    )
    session.commit()

    response = test_client.post("/transactions/categorize", headers=auth_headers(user), json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed"] == 1
    assert payload["updated"] == 1
    assert payload["skipped_manual"] == 1
    session.refresh(auto)
    session.refresh(manual)
    assert auto.category == "subscriptions"
    assert auto.category_source == "auto"
    assert manual.category == "food"
    assert manual.category_source == "manual"


def test_force_requires_overwrite_manual_for_manual_categories(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    upload = seed_upload(session, user["user"]["id"])
    manual = add_transaction(
        session,
        user_id=user["user"]["id"],
        upload_id=upload.id,
        merchant="Grab",
        description="Grab ride",
        category="food",
        category_source="manual",
        manual=True,
    )
    session.commit()

    force_only = test_client.post(
        "/transactions/categorize",
        headers=auth_headers(user),
        json={"force": True, "transaction_ids": [str(manual.id)]},
    )
    session.refresh(manual)
    assert force_only.status_code == 200
    assert force_only.json()["skipped_manual"] == 1
    assert manual.category == "food"

    overwrite = test_client.post(
        "/transactions/categorize",
        headers=auth_headers(user),
        json={"force": True, "overwrite_manual": True, "transaction_ids": [str(manual.id)]},
    )
    session.refresh(manual)
    assert overwrite.status_code == 200
    assert manual.category == "transportation"
    assert manual.category_source == "auto"
    assert manual.category_manually_set is False


def test_categorize_route_auth_scoping_and_id_limits(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    other = register_user(test_client, "other-categorizer@example.com")
    upload = seed_upload(session, other["user"]["id"])
    other_transaction = add_transaction(
        session,
        user_id=other["user"]["id"],
        upload_id=upload.id,
        merchant="Netflix",
        description="Netflix subscription",
    )
    session.commit()

    unauthenticated = test_client.post("/transactions/categorize", json={})
    cross_user = test_client.post(
        "/transactions/categorize",
        headers=auth_headers(user),
        json={"transaction_ids": [str(other_transaction.id)]},
    )
    too_many_ids = test_client.post(
        "/transactions/categorize",
        headers=auth_headers(user),
        json={"transaction_ids": [str(other_transaction.id)] * 101},
    )

    assert unauthenticated.status_code == 401
    assert cross_user.status_code == 200
    assert cross_user.json()["processed"] == 0
    session.refresh(other_transaction)
    assert other_transaction.category is None
    assert too_many_ids.status_code == 422


def test_categorization_summary_and_audit_logs(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    upload = seed_upload(session, user["user"]["id"])
    add_transaction(session, user_id=user["user"]["id"], upload_id=upload.id, merchant="Netflix", description="")
    add_transaction(session, user_id=user["user"]["id"], upload_id=upload.id, merchant="Mystery", description="Reference")
    session.commit()

    categorize = test_client.post("/transactions/categorize", headers=auth_headers(user), json={})
    summary = test_client.get("/transactions/categories/summary", headers=auth_headers(user))

    assert categorize.status_code == 200
    assert categorize.json()["needs_review"] == 1
    assert categorize.json()["categories"]["needs_review"] == 1
    assert summary.status_code == 200
    summary_counts = {item["category"]: item["transaction_count"] for item in summary.json()["items"]}
    assert summary_counts["subscriptions"] == 1
    assert summary_counts["needs_review"] == 1
    actions = {log.action for log in session.exec(select(AuditLog)).all()}
    assert "transaction.categorized" in actions
    assert "transaction.bulk_categorized" in actions
