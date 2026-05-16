from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import AuditLog, Subscription, Transaction, TransactionUpload


def register_user(test_client: TestClient, email: str = "subscriptions@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def seed_recurring_transactions(session: Session, user_id: str, merchant: str = "Netflix") -> None:
    upload = TransactionUpload(
        user_id=UUID(user_id),
        file_name="seed.csv",
        upload_status="completed",
        total_rows=4,
        processed_rows=4,
    )
    session.add(upload)
    session.flush()
    for transaction_date in [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]:
        session.add(
            Transaction(
                user_id=UUID(user_id),
                upload_id=upload.id,
                transaction_date=transaction_date,
                merchant_raw=merchant,
                merchant_normalized=merchant.lower(),
                description=f"{merchant} Subscription",
                amount=Decimal("-549.00"),
                currency="PHP",
                category="subscriptions",
                category_source="auto",
            )
        )
    session.commit()


def csv_file(content: str, filename: str = "subscriptions.csv") -> dict:
    return {"file": (filename, BytesIO(content.encode("utf-8")), "text/csv")}


def test_detect_and_list_subscriptions_require_auth(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    detect_response = test_client.post("/subscriptions/detect")
    list_response = test_client.get("/subscriptions")

    assert detect_response.status_code == 401
    assert list_response.status_code == 401


def test_detect_subscriptions_and_prevent_duplicates(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_recurring_transactions(session, user["user"]["id"])

    first = test_client.post("/subscriptions/detect", headers=auth_headers(user))
    second = test_client.post("/subscriptions/detect", headers=auth_headers(user))

    assert first.status_code == 200
    assert first.json()["detected_count"] == 1
    assert first.json()["updated_count"] == 0
    assert second.status_code == 200
    assert second.json()["detected_count"] == 1
    assert second.json()["updated_count"] == 1
    assert len(session.exec(select(Subscription)).all()) == 1


def test_get_subscriptions_returns_only_current_user(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "first-subscriptions@example.com")
    second_user = register_user(test_client, "second-subscriptions@example.com")
    seed_recurring_transactions(session, first_user["user"]["id"], merchant="Netflix")
    seed_recurring_transactions(session, second_user["user"]["id"], merchant="Spotify")
    test_client.post("/subscriptions/detect", headers=auth_headers(first_user))
    test_client.post("/subscriptions/detect", headers=auth_headers(second_user))

    response = test_client.get("/subscriptions", headers=auth_headers(first_user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["subscriptions"][0]["merchant_name"] == "Netflix"
    assert "user_id" not in payload["subscriptions"][0]


def test_get_subscription_blocks_cross_user_access(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "own-subscription@example.com")
    second_user = register_user(test_client, "cross-subscription@example.com")
    seed_recurring_transactions(session, first_user["user"]["id"])
    detected = test_client.post("/subscriptions/detect", headers=auth_headers(first_user)).json()
    subscription_id = detected["subscriptions"][0]["id"]

    own_response = test_client.get(f"/subscriptions/{subscription_id}", headers=auth_headers(first_user))
    cross_user_response = test_client.get(f"/subscriptions/{subscription_id}", headers=auth_headers(second_user))

    assert own_response.status_code == 200
    assert own_response.json()["merchant_name"] == "Netflix"
    assert cross_user_response.status_code == 404


def test_subscription_filters(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_recurring_transactions(session, user["user"]["id"], merchant="Netflix")
    test_client.post("/subscriptions/detect", headers=auth_headers(user))

    by_status = test_client.get("/subscriptions?status=active", headers=auth_headers(user))
    by_frequency = test_client.get("/subscriptions?frequency=monthly", headers=auth_headers(user))
    by_search = test_client.get("/subscriptions?search=net", headers=auth_headers(user))
    invalid_limit = test_client.get("/subscriptions?limit=101", headers=auth_headers(user))

    assert by_status.status_code == 200
    assert by_frequency.json()["count"] == 1
    assert by_search.json()["count"] == 1
    assert invalid_limit.status_code == 422
    assert invalid_limit.json() == {"detail": "Invalid request payload."}


def test_patch_subscription_status_prevents_mass_assignment_and_audits(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_recurring_transactions(session, user["user"]["id"])
    detected = test_client.post("/subscriptions/detect", headers=auth_headers(user)).json()
    subscription_id = detected["subscriptions"][0]["id"]

    mass_assignment = test_client.patch(
        f"/subscriptions/{subscription_id}/status",
        headers=auth_headers(user),
        json={"status": "paused", "average_amount": "1.00", "user_id": user["user"]["id"]},
    )
    valid = test_client.patch(
        f"/subscriptions/{subscription_id}/status",
        headers=auth_headers(user),
        json={"status": "paused"},
    )

    assert mass_assignment.status_code == 422
    assert valid.status_code == 200
    assert valid.json()["status"] == "paused"
    subscription = session.get(Subscription, UUID(subscription_id))
    assert subscription is not None
    assert subscription.average_amount == Decimal("549.00")
    audit_log = session.exec(select(AuditLog).where(AuditLog.action == "subscription.status_changed")).one()
    assert audit_log.metadata_json["new_status"] == "paused"


def test_detection_preserves_manually_changed_status(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_recurring_transactions(session, user["user"]["id"])
    detected = test_client.post("/subscriptions/detect", headers=auth_headers(user)).json()
    subscription_id = detected["subscriptions"][0]["id"]
    test_client.patch(
        f"/subscriptions/{subscription_id}/status",
        headers=auth_headers(user),
        json={"status": "paused"},
    )

    response = test_client.post("/subscriptions/detect", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["subscriptions"][0]["status"] == "paused"


def test_detect_safe_when_user_has_no_transactions(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post("/subscriptions/detect", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["subscriptions"] == []
    assert response.json()["detected_count"] == 0


def test_csv_import_runs_subscription_detection(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    content = """date,description,merchant,amount,currency
2026-01-01,Netflix Subscription,Netflix,-549,PHP
2026-02-01,Netflix Subscription,Netflix,-549,PHP
2026-03-01,Netflix Subscription,Netflix,-549,PHP
"""

    response = test_client.post("/uploads/csv", headers=auth_headers(user), files=csv_file(content))

    assert response.status_code == 201
    subscriptions = session.exec(select(Subscription)).all()
    assert len(subscriptions) == 1
    assert subscriptions[0].merchant_name == "Netflix"
