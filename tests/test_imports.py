from io import BytesIO
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.imports import get_import_rate_limiter
from app.core.rate_limit import InMemoryRateLimiter
from app.models import AuditLog, Transaction, TransactionUpload


def register_user(test_client: TestClient, email: str = "importer@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def csv_file(content: str, filename: str = "transactions.csv") -> dict:
    return {"file": (filename, BytesIO(content.encode("utf-8")), "text/csv")}


valid_csv = """date,description,merchant,amount,currency
2026-01-01,Netflix Subscription,Netflix,-549,PHP
2026-01-03,Grab Ride,Grab,-230,PHP
"""


def test_valid_csv_upload(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post("/uploads/csv", headers=auth_headers(user), files=csv_file(valid_csv))

    assert response.status_code == 201
    assert response.json()["processed_rows"] == 2
    transactions = session.exec(select(Transaction)).all()
    assert len(transactions) == 2
    assert {transaction.user_id for transaction in transactions} == {UUID(user["user"]["id"])}
    assert transactions[0].merchant_normalized == "netflix"
    assert transactions[0].category == "subscriptions"
    assert transactions[0].category_source == "auto"


def test_csv_upload_missing_required_column(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    content = "date,description,amount,currency\n2026-01-01,Netflix,-549,PHP\n"

    response = test_client.post("/uploads/csv", headers=auth_headers(user), files=csv_file(content))

    assert response.status_code == 400
    assert response.json() == {"detail": "CSV is missing required columns."}


def test_csv_upload_invalid_date_format(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    content = "date,description,merchant,amount,currency\n01/01/2026,Netflix,Netflix,-549,PHP\n"

    response = test_client.post("/uploads/csv", headers=auth_headers(user), files=csv_file(content))

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid date."}


def test_csv_upload_invalid_amount(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    content = "date,description,merchant,amount,currency\n2026-01-01,Netflix,Netflix,nope,PHP\n"

    response = test_client.post("/uploads/csv", headers=auth_headers(user), files=csv_file(content))

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid amount."}


def test_csv_duplicate_transaction_prevention(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    first = test_client.post("/uploads/csv", headers=auth_headers(user), files=csv_file(valid_csv))
    second = test_client.post("/uploads/csv", headers=auth_headers(user), files=csv_file(valid_csv))

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["processed_rows"] == 0
    assert second.json()["duplicate_rows"] == 2
    assert len(session.exec(select(Transaction)).all()) == 2


def test_csv_upload_belongs_only_to_authenticated_user(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "one@example.com")
    second_user = register_user(test_client, "two@example.com")
    upload = test_client.post("/uploads/csv", headers=auth_headers(first_user), files=csv_file(valid_csv)).json()

    own_response = test_client.get(f"/uploads/{upload['upload_id']}", headers=auth_headers(first_user))
    cross_user_response = test_client.get(f"/uploads/{upload['upload_id']}", headers=auth_headers(second_user))

    assert own_response.status_code == 200
    assert cross_user_response.status_code == 404


def test_manual_transaction_creation(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/transactions/manual",
        headers=auth_headers(user),
        json={
            "transaction_date": "2026-01-04",
            "merchant": " Company Payroll ",
            "description": "Salary",
            "amount": "35000",
            "currency": "php",
            "category": "income",
        },
    )

    assert response.status_code == 201
    assert response.json()["transaction"]["merchant_normalized"] == "company payroll"
    assert response.json()["transaction"]["category_source"] == "manual"
    transaction = session.exec(select(Transaction)).one()
    assert transaction.user_id == UUID(user["user"]["id"])
    assert transaction.amount == Decimal("35000.00")
    assert transaction.category_manually_set is True


def test_manual_transaction_without_category_is_auto_categorized(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/transactions/manual",
        headers=auth_headers(user),
        json={
            "transaction_date": "2026-01-04",
            "merchant": "Starbucks",
            "description": "Coffee",
            "amount": "-180",
            "currency": "PHP",
        },
    )

    assert response.status_code == 201
    transaction = session.exec(select(Transaction)).one()
    assert transaction.category == "food"
    assert transaction.category_source == "auto"
    assert transaction.category_manually_set is False


def test_manual_transaction_validation_errors(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/transactions/manual",
        headers=auth_headers(user),
        json={
            "transaction_date": "2026-01-04",
            "merchant": "",
            "description": "Salary",
            "amount": "0",
            "currency": "PHP",
            "user_id": user["user"]["id"],
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request payload."}


def test_manual_transaction_duplicate_prevention(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    payload = {
        "transaction_date": "2026-01-04",
        "merchant": "Company Payroll",
        "description": "Salary",
        "amount": "35000",
        "currency": "PHP",
    }

    first = test_client.post("/transactions/manual", headers=auth_headers(user), json=payload)
    second = test_client.post("/transactions/manual", headers=auth_headers(user), json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert len(session.exec(select(Transaction)).all()) == 1


def test_paste_preview_with_valid_rows(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/imports/paste/preview",
        headers=auth_headers(user),
        json={"text": "2026-01-01 Netflix Subscription Netflix -549 PHP\nJan 3 Grab -230 PHP"},
    )

    assert response.status_code == 200
    assert len(response.json()["valid_rows"]) == 2
    assert response.json()["invalid_rows"] == []


def test_paste_preview_with_invalid_rows(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/imports/paste/preview",
        headers=auth_headers(user),
        json={"text": "2026-01-01 Netflix -549 PHP\nnot enough\nJan X Grab -230 PHP"},
    )

    assert response.status_code == 200
    assert len(response.json()["valid_rows"]) == 1
    assert len(response.json()["invalid_rows"]) == 2


def test_paste_confirm_revalidates_server_side(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/imports/paste/confirm",
        headers=auth_headers(user),
        json={"text": "2026-01-01 Netflix Subscription Netflix -549 PHP\nbad row"},
    )

    assert response.status_code == 201
    assert response.json()["processed_rows"] == 1
    assert len(response.json()["invalid_rows"]) == 1
    transaction = session.exec(select(Transaction)).one()
    assert transaction.category == "subscriptions"
    assert transaction.category_source == "auto"


def test_paste_import_rejects_oversized_input(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    response = test_client.post(
        "/imports/paste/preview",
        headers=auth_headers(user),
        json={"text": "x" * 100_001},
    )

    assert response.status_code == 413


def test_demo_data_loads_for_current_user_only(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    first_user = register_user(test_client, "demo-one@example.com")
    second_user = register_user(test_client, "demo-two@example.com")

    response = test_client.post(
        "/demo/load-sample-data",
        headers=auth_headers(first_user),
        json={"allow_overwrite": False},
    )

    assert response.status_code == 201
    first_transactions = session.exec(
        select(Transaction).where(Transaction.user_id == UUID(first_user["user"]["id"]))
    ).all()
    second_transactions = session.exec(
        select(Transaction).where(Transaction.user_id == UUID(second_user["user"]["id"]))
    ).all()
    assert len(first_transactions) == 4
    assert second_transactions == []
    categories = {transaction.merchant_raw: transaction.category for transaction in first_transactions}
    assert categories["Netflix"] == "subscriptions"
    assert categories["Grab"] == "transportation"
    assert categories["Company Payroll"] == "income"


def test_demo_data_deduplicates_without_overwrite(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    first = test_client.post("/demo/load-sample-data", headers=auth_headers(user), json={"allow_overwrite": False})
    second = test_client.post("/demo/load-sample-data", headers=auth_headers(user), json={"allow_overwrite": False})

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["duplicate_rows"] == 4
    assert len(session.exec(select(Transaction)).all()) == 4


def test_unauthorized_users_cannot_access_import_routes(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    upload_response = test_client.post("/uploads/csv", files=csv_file(valid_csv))
    manual_response = test_client.post("/transactions/manual", json={})
    paste_response = test_client.post("/imports/paste/preview", json={"text": "Jan 1 Netflix -549 PHP"})
    demo_response = test_client.post("/demo/load-sample-data", json={"allow_overwrite": False})

    assert upload_response.status_code == 401
    assert manual_response.status_code == 401
    assert paste_response.status_code == 401
    assert demo_response.status_code == 401


def test_audit_logs_created_without_sensitive_raw_content(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    test_client.post("/uploads/csv", headers=auth_headers(user), files=csv_file(valid_csv))
    test_client.post(
        "/transactions/manual",
        headers=auth_headers(user),
        json={
            "transaction_date": "2026-01-04",
            "merchant": "Company Payroll",
            "description": "Sensitive salary note",
            "amount": "35000",
            "currency": "PHP",
        },
    )
    test_client.post(
        "/imports/paste/confirm",
        headers=auth_headers(user),
        json={"text": "2026-01-09 Private Description Store -100 PHP"},
    )
    test_client.post("/demo/load-sample-data", headers=auth_headers(user), json={"allow_overwrite": False})

    actions = {
        "transaction_upload.csv_uploaded",
        "transaction.manual_created",
        "transaction_import.paste_confirmed",
        "transaction_import.demo_data_loaded",
    }
    logs = session.exec(select(AuditLog).where(AuditLog.action.in_(actions))).all()
    serialized = str([log.metadata_json for log in logs])
    assert actions == {log.action for log in logs}
    assert "Sensitive salary note" not in serialized
    assert "Private Description" not in serialized
    assert "Netflix Subscription" not in serialized


def test_import_rate_limit_behavior(client) -> None:  # noqa: ANN001
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    client.dependency_overrides[get_import_rate_limiter] = lambda: limiter
    test_client = TestClient(client)
    user = register_user(test_client)

    first = test_client.post("/imports/paste/preview", headers=auth_headers(user), json={"text": "Jan 1 Netflix -549 PHP"})
    second = test_client.post("/imports/paste/preview", headers=auth_headers(user), json={"text": "Jan 2 Grab -230 PHP"})

    assert first.status_code == 200
    assert second.status_code == 429
