from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.privacy import get_privacy_rate_limiter
from app.core.rate_limit import InMemoryRateLimiter
from app.models import MonthlyInsightReport, SpendingAnomaly, Subscription, Transaction, TransactionUpload, User
from app.schemas.privacy import DELETE_ACCOUNT_CONFIRMATION, DELETE_APP_DATA_CONFIRMATION


def register_user(test_client: TestClient, email: str = "privacy@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def create_upload(
    *,
    session: Session,
    user_id: UUID,
    file_name: str,
) -> TransactionUpload:
    upload = TransactionUpload(
        user_id=user_id,
        file_name=file_name,
        upload_status="completed",
        total_rows=1,
        processed_rows=1,
    )
    session.add(upload)
    session.flush()
    return upload


def create_transaction(
    *,
    session: Session,
    user_id: UUID,
    upload_id: UUID,
    merchant: str = "Coffee Bar",
) -> Transaction:
    transaction = Transaction(
        user_id=user_id,
        upload_id=upload_id,
        transaction_date=date(2026, 5, 1),
        merchant_raw=merchant,
        merchant_normalized=merchant.lower(),
        description="Normalized app transaction",
        amount=Decimal("-120.00"),
        currency="PHP",
        category="food",
        category_source="manual",
    )
    session.add(transaction)
    session.flush()
    return transaction


def create_derived_records(*, session: Session, user_id: UUID) -> None:
    session.add(
        Subscription(
            user_id=user_id,
            merchant_name="Stream Box",
            average_amount=Decimal("199.00"),
            frequency="monthly",
            first_seen=date(2026, 1, 1),
            last_seen=date(2026, 5, 1),
            confidence_score=0.94,
        )
    )
    session.add(
        SpendingAnomaly(
            user_id=user_id,
            anomaly_type="CATEGORY_SPIKE",
            category="food",
            amount_delta=Decimal("500.00"),
            explanation="Food spending changed compared with the baseline.",
            severity="medium",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
    )
    session.add(
        MonthlyInsightReport(
            user_id=user_id,
            month=date(2026, 5, 1),
            total_spend=Decimal("120.00"),
            total_income=Decimal("0.00"),
            net_flow=Decimal("-120.00"),
            transaction_count=1,
            top_categories_json={"items": []},
            detected_subscriptions_json=[],
            anomalies_json=[],
            ai_summary="Neutral imported-data summary.",
            safety_flags_json=["not_financial_advice"],
        )
    )
    session.commit()


def test_privacy_summary_returns_only_current_user_counts_and_safe_notes(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "privacy-one@example.com")
    second_user = register_user(test_client, "privacy-two@example.com")

    demo_response = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(first_user),
        json={"allow_overwrite": False},
    )
    assert demo_response.status_code == 201
    second_upload = create_upload(
        session=session,
        user_id=UUID(second_user["user"]["id"]),
        file_name="transactions.csv",
    )
    create_transaction(
        session=session,
        user_id=UUID(second_user["user"]["id"]),
        upload_id=second_upload.id,
        merchant="Other User Merchant",
    )
    session.commit()

    response = test_client.get("/settings/privacy/summary", headers=auth_headers(first_user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_email"] == "privacy-one@example.com"
    assert payload["transaction_count"] == demo_response.json()["processed_rows"]
    assert payload["has_demo_data"] is True
    assert payload["data_sources_used"]["demo_data"] is True
    assert payload["data_sources_used"]["csv_upload"] is False
    assert "Tally does not connect to banks." in payload["privacy_notes"]
    assert "Tally does not provide financial advice." in payload["privacy_notes"]
    serialized = str(payload)
    assert "password_hash" not in serialized
    assert "Other User Merchant" not in serialized


def test_export_includes_current_user_records_and_excludes_sensitive_or_cross_user_data(
    client,
    session: Session,
) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "export-one@example.com")
    second_user = register_user(test_client, "export-two@example.com")
    first_user_id = UUID(first_user["user"]["id"])
    second_user_id = UUID(second_user["user"]["id"])
    first_upload = create_upload(session=session, user_id=first_user_id, file_name="transactions.csv")
    second_upload = create_upload(session=session, user_id=second_user_id, file_name="other.csv")
    create_transaction(session=session, user_id=first_user_id, upload_id=first_upload.id, merchant="Own Merchant")
    create_transaction(session=session, user_id=second_user_id, upload_id=second_upload.id, merchant="Other Merchant")
    create_derived_records(session=session, user_id=first_user_id)

    response = test_client.get("/settings/privacy/export", headers=auth_headers(first_user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["app"] == "Tally"
    assert payload["metadata"]["scope"] == "current_user"
    assert payload["metadata"]["notice"].startswith("This export contains Tally app data")
    assert payload["user"]["email"] == "export-one@example.com"
    assert len(payload["transactions"]) == 1
    assert len(payload["subscriptions"]) == 1
    assert len(payload["anomalies"]) == 1
    assert len(payload["monthly_reports"]) == 1
    serialized = str(payload)
    assert "Own Merchant" in serialized
    assert "Other Merchant" not in serialized
    assert "export-two@example.com" not in serialized
    assert "password_hash" not in serialized
    assert "token" not in serialized.lower()
    assert "secret" not in serialized.lower()


def test_clear_demo_data_removes_only_marked_demo_uploads_and_clears_derived_records(
    client,
    session: Session,
) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    user_id = UUID(user["user"]["id"])
    assert test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(user),
        json={"allow_overwrite": False},
    ).status_code == 201
    manual_upload = create_upload(session=session, user_id=user_id, file_name="manual-entry")
    create_transaction(session=session, user_id=user_id, upload_id=manual_upload.id, merchant="Manual Keeper")
    create_derived_records(session=session, user_id=user_id)

    response = test_client.post("/settings/privacy/clear-demo-data", headers=auth_headers(user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Demo data cleared."
    assert payload["deleted_counts"]["transactions"] > 0
    remaining_transactions = session.exec(select(Transaction).where(Transaction.user_id == user_id)).all()
    assert len(remaining_transactions) == 1
    assert remaining_transactions[0].merchant_raw == "Manual Keeper"
    remaining_uploads = session.exec(select(TransactionUpload).where(TransactionUpload.user_id == user_id)).all()
    assert {upload.file_name for upload in remaining_uploads} == {"manual-entry"}
    assert session.exec(select(Subscription).where(Subscription.user_id == user_id)).all() == []
    assert session.exec(select(SpendingAnomaly).where(SpendingAnomaly.user_id == user_id)).all() == []
    assert session.exec(select(MonthlyInsightReport).where(MonthlyInsightReport.user_id == user_id)).all() == []


def test_delete_app_data_requires_exact_confirmation_and_preserves_account_and_other_users(
    client,
    session: Session,
) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "delete-data-one@example.com")
    second_user = register_user(test_client, "delete-data-two@example.com")
    first_user_id = UUID(first_user["user"]["id"])
    second_user_id = UUID(second_user["user"]["id"])
    first_upload = create_upload(session=session, user_id=first_user_id, file_name="transactions.csv")
    second_upload = create_upload(session=session, user_id=second_user_id, file_name="transactions.csv")
    create_transaction(session=session, user_id=first_user_id, upload_id=first_upload.id)
    create_transaction(session=session, user_id=second_user_id, upload_id=second_upload.id)
    create_derived_records(session=session, user_id=first_user_id)

    wrong = test_client.post(
        "/settings/privacy/delete-app-data",
        headers=auth_headers(first_user),
        json={"confirmation": "delete my tally data"},
    )
    assert wrong.status_code == 422
    assert wrong.json() == {"detail": "Invalid request payload."}

    response = test_client.post(
        "/settings/privacy/delete-app-data",
        headers=auth_headers(first_user),
        json={"confirmation": DELETE_APP_DATA_CONFIRMATION},
    )

    assert response.status_code == 200
    assert response.json()["deleted_counts"]["transactions"] == 1
    assert session.get(User, first_user_id) is not None
    assert test_client.get("/auth/me", headers=auth_headers(first_user)).status_code == 200
    assert session.exec(select(Transaction).where(Transaction.user_id == first_user_id)).all() == []
    assert len(session.exec(select(Transaction).where(Transaction.user_id == second_user_id)).all()) == 1


def test_delete_account_requires_exact_confirmation_and_removes_only_current_user(
    client,
    session: Session,
) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "delete-account-one@example.com")
    second_user = register_user(test_client, "delete-account-two@example.com")
    first_user_id = UUID(first_user["user"]["id"])
    second_user_id = UUID(second_user["user"]["id"])
    first_upload = create_upload(session=session, user_id=first_user_id, file_name="transactions.csv")
    second_upload = create_upload(session=session, user_id=second_user_id, file_name="transactions.csv")
    create_transaction(session=session, user_id=first_user_id, upload_id=first_upload.id)
    create_transaction(session=session, user_id=second_user_id, upload_id=second_upload.id)

    wrong = test_client.post(
        "/settings/privacy/delete-account",
        headers=auth_headers(first_user),
        json={"confirmation": "DELETE ACCOUNT"},
    )
    assert wrong.status_code == 422

    response = test_client.post(
        "/settings/privacy/delete-account",
        headers=auth_headers(first_user),
        json={"confirmation": DELETE_ACCOUNT_CONFIRMATION},
    )

    assert response.status_code == 200
    assert response.json()["deleted_counts"]["user"] == 1
    assert session.get(User, first_user_id) is None
    assert session.get(User, second_user_id) is not None
    assert test_client.get("/auth/me", headers=auth_headers(first_user)).status_code == 401
    assert test_client.get("/auth/me", headers=auth_headers(second_user)).status_code == 200
    assert len(session.exec(select(Transaction).where(Transaction.user_id == second_user_id)).all()) == 1


def test_unauthenticated_users_cannot_access_privacy_routes(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    responses = [
        test_client.get("/settings/privacy/summary"),
        test_client.get("/settings/privacy/export"),
        test_client.post("/settings/privacy/clear-demo-data"),
        test_client.post("/settings/privacy/delete-app-data", json={"confirmation": DELETE_APP_DATA_CONFIRMATION}),
        test_client.post("/settings/privacy/delete-account", json={"confirmation": DELETE_ACCOUNT_CONFIRMATION}),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401, 401, 401]


def test_privacy_routes_have_safe_validation_errors_and_rate_limit(client) -> None:  # noqa: ANN001
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    client.dependency_overrides[get_privacy_rate_limiter] = lambda: limiter
    test_client = TestClient(client)
    user = register_user(test_client)

    first = test_client.get("/settings/privacy/summary", headers=auth_headers(user))
    second = test_client.get("/settings/privacy/summary", headers=auth_headers(user))
    assert first.status_code == 200
    assert second.status_code == 429

    limiter.clear()
    malformed = test_client.post(
        "/settings/privacy/delete-app-data",
        headers=auth_headers(user),
        json={"confirmation": DELETE_APP_DATA_CONFIRMATION, "user_id": user["user"]["id"]},
    )
    assert malformed.status_code == 422
    assert malformed.json() == {"detail": "Invalid request payload."}
    assert "Traceback" not in malformed.text

