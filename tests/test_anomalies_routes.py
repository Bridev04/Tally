from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import SpendingAnomaly, Transaction, TransactionUpload


def register_user(test_client: TestClient, email: str = "anomalies@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def seed_anomaly_transactions(session: Session, user_id: str, merchant: str = "Cafe") -> None:
    upload = TransactionUpload(
        user_id=UUID(user_id),
        file_name="seed-anomalies.csv",
        upload_status="completed",
        total_rows=4,
        processed_rows=4,
    )
    session.add(upload)
    session.flush()
    rows = [
        (date(2026, 4, 1), merchant, "-1000.00", "food", "Lunch receipt with private note"),
        (date(2026, 5, 1), merchant, "-1800.00", "food", "Lunch receipt with private note"),
        (date(2026, 5, 2), merchant, "-1800.00", "food", "Lunch receipt with private note"),
        (date(2026, 5, 3), "Unknown Shop", "-50.00", "needs_review", "Sensitive imported memo"),
    ]
    for transaction_date, row_merchant, amount, category, description in rows:
        session.add(
            Transaction(
                user_id=UUID(user_id),
                upload_id=upload.id,
                transaction_date=transaction_date,
                merchant_raw=row_merchant,
                merchant_normalized=row_merchant.lower(),
                description=description,
                amount=Decimal(amount),
                currency="PHP",
                category=category,
                category_confidence=0.95,
                category_source="auto",
            )
        )
    session.commit()


def test_anomaly_routes_require_auth(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    detect_response = test_client.post("/anomalies/detect", json={})
    list_response = test_client.get("/anomalies")
    summary_response = test_client.get("/anomalies/summary")

    assert detect_response.status_code == 401
    assert list_response.status_code == 401
    assert summary_response.status_code == 401


def test_detect_creates_anomalies_for_current_user_only(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "first-anomalies@example.com")
    second_user = register_user(test_client, "second-anomalies@example.com")
    seed_anomaly_transactions(session, first_user["user"]["id"], merchant="Cafe")
    seed_anomaly_transactions(session, second_user["user"]["id"], merchant="Bakery")

    response = test_client.post(
        "/anomalies/detect",
        headers=auth_headers(first_user),
        json={"month": "2026-05"},
    )
    no_body_response = test_client.post("/anomalies/detect", headers=auth_headers(first_user))
    first_list = test_client.get("/anomalies?month=2026-05", headers=auth_headers(first_user))
    second_list = test_client.get("/anomalies?month=2026-05", headers=auth_headers(second_user))

    assert response.status_code == 200
    assert no_body_response.status_code == 200
    assert response.json()["detected_count"] >= 1
    assert first_list.json()["count"] == response.json()["detected_count"]
    assert second_list.json()["count"] == 0
    assert all(item["merchant_name"] != "Bakery" for item in first_list.json()["anomalies"])


def test_detect_is_idempotent_and_audited(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_anomaly_transactions(session, user["user"]["id"])

    first = test_client.post("/anomalies/detect", headers=auth_headers(user), json={"month": "2026-05"})
    second = test_client.post("/anomalies/detect", headers=auth_headers(user), json={"month": "2026-05"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["detected_count"] == first.json()["detected_count"]
    assert len(session.exec(select(SpendingAnomaly)).all()) == first.json()["detected_count"]


def test_get_anomalies_supports_filters_and_limit_bounds(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_anomaly_transactions(session, user["user"]["id"])
    test_client.post("/anomalies/detect", headers=auth_headers(user), json={"month": "2026-05"})

    by_type = test_client.get(
        "/anomalies?month=2026-05&anomaly_type=CATEGORY_SPIKE",
        headers=auth_headers(user),
    )
    by_severity = test_client.get("/anomalies?severity=medium", headers=auth_headers(user))
    invalid_limit = test_client.get("/anomalies?limit=101", headers=auth_headers(user))

    assert by_type.status_code == 200
    assert all(item["anomaly_type"] == "CATEGORY_SPIKE" for item in by_type.json()["anomalies"])
    assert by_severity.status_code == 200
    assert invalid_limit.status_code == 422
    assert invalid_limit.json() == {"detail": "Invalid request payload."}


def test_summary_returns_counts(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_anomaly_transactions(session, user["user"]["id"])
    test_client.post("/anomalies/detect", headers=auth_headers(user), json={"month": "2026-05"})

    response = test_client.get("/anomalies/summary?month=2026-05", headers=auth_headers(user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["month"] == "2026-05"
    assert payload["total_anomalies"] >= 1
    assert payload["high_count"] + payload["medium_count"] + payload["low_count"] == payload["total_anomalies"]
    assert payload["top_categories"]


def test_invalid_month_returns_safe_validation_error(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    detect_response = test_client.post(
        "/anomalies/detect",
        headers=auth_headers(user),
        json={"month": "05-2026"},
    )
    list_response = test_client.get("/anomalies?month=2026-99", headers=auth_headers(user))

    assert detect_response.status_code == 422
    assert detect_response.json() == {"detail": "Invalid request payload."}
    assert list_response.status_code == 422
    assert list_response.json() == {"detail": "Invalid request payload."}


def test_no_raw_sensitive_transaction_contents_or_stack_traces(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_anomaly_transactions(session, user["user"]["id"])

    response = test_client.post("/anomalies/detect", headers=auth_headers(user), json={"month": "2026-05"})
    malformed = test_client.get("/anomalies?offset=-1", headers=auth_headers(user))
    payload_text = str(response.json()).lower()

    assert response.status_code == 200
    assert "private note" not in payload_text
    assert "sensitive imported memo" not in payload_text
    assert "traceback" not in malformed.text.lower()
    assert "internal" not in malformed.text.lower()
