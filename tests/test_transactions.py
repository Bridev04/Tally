from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.transactions import get_transaction_rate_limiter
from app.core.rate_limit import InMemoryRateLimiter
from app.models import AuditLog, Transaction, TransactionUpload


def register_user(test_client: TestClient, email: str = "viewer@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def seed_transactions(session: Session, user_id: str) -> list[Transaction]:
    upload = TransactionUpload(
        user_id=UUID(user_id),
        file_name="seed.csv",
        upload_status="completed",
        total_rows=4,
        processed_rows=4,
    )
    session.add(upload)
    session.flush()
    transactions = [
        Transaction(
            user_id=UUID(user_id),
            upload_id=upload.id,
            transaction_date=date(2026, 1, 10),
            merchant_raw="Netflix",
            merchant_normalized="netflix",
            description="Monthly subscription",
            amount=Decimal("-549.00"),
            currency="PHP",
            category="subscriptions",
            category_confidence=0.80,
            payment_type="card",
        ),
        Transaction(
            user_id=UUID(user_id),
            upload_id=upload.id,
            transaction_date=date(2026, 1, 8),
            merchant_raw="Grab",
            merchant_normalized="grab",
            description="Ride to office",
            amount=Decimal("-230.00"),
            currency="PHP",
            category="transportation",
            payment_type="card",
        ),
        Transaction(
            user_id=UUID(user_id),
            upload_id=upload.id,
            transaction_date=date(2026, 1, 5),
            merchant_raw="Coffee Bar",
            merchant_normalized="coffee bar",
            description="Flat white",
            amount=Decimal("-150.00"),
            currency="PHP",
            category="food",
            payment_type="cash",
        ),
        Transaction(
            user_id=UUID(user_id),
            upload_id=upload.id,
            transaction_date=date(2026, 1, 1),
            merchant_raw="Company Payroll",
            merchant_normalized="company payroll",
            description="Salary",
            amount=Decimal("35000.00"),
            currency="PHP",
            category="income",
            payment_type="bank",
        ),
    ]
    session.add_all(transactions)
    session.commit()
    return transactions


def test_list_transactions_for_authenticated_user(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    other = register_user(test_client, "other-viewer@example.com")
    seed_transactions(session, user["user"]["id"])
    seed_transactions(session, other["user"]["id"])

    response = test_client.get("/transactions", headers=auth_headers(user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 4
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert [item["merchant_raw"] for item in payload["transactions"]] == [
        "Netflix",
        "Grab",
        "Coffee Bar",
        "Company Payroll",
    ]
    assert all("user_id" not in item for item in payload["transactions"])


def test_list_transactions_requires_auth(client) -> None:  # noqa: ANN001
    response = TestClient(client).get("/transactions")

    assert response.status_code == 401


def test_list_transactions_filters(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_transactions(session, user["user"]["id"])

    by_category = test_client.get("/transactions?category=subscriptions", headers=auth_headers(user))
    by_date = test_client.get(
        "/transactions?date_from=2026-01-05&date_to=2026-01-08",
        headers=auth_headers(user),
    )
    by_merchant = test_client.get("/transactions?merchant=grab", headers=auth_headers(user))
    by_search = test_client.get("/transactions?search=flat", headers=auth_headers(user))
    by_payment = test_client.get("/transactions?payment_type=cash", headers=auth_headers(user))
    by_amount = test_client.get("/transactions?min_amount=-300&max_amount=-100", headers=auth_headers(user))

    assert [item["merchant_raw"] for item in by_category.json()["transactions"]] == ["Netflix"]
    assert [item["merchant_raw"] for item in by_date.json()["transactions"]] == ["Grab", "Coffee Bar"]
    assert [item["merchant_raw"] for item in by_merchant.json()["transactions"]] == ["Grab"]
    assert [item["merchant_raw"] for item in by_search.json()["transactions"]] == ["Coffee Bar"]
    assert [item["merchant_raw"] for item in by_payment.json()["transactions"]] == ["Coffee Bar"]
    assert [item["merchant_raw"] for item in by_amount.json()["transactions"]] == ["Grab", "Coffee Bar"]


def test_pagination_and_limit_max_validation(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_transactions(session, user["user"]["id"])

    page = test_client.get("/transactions?limit=2&offset=1", headers=auth_headers(user))
    too_large = test_client.get("/transactions?limit=101", headers=auth_headers(user))

    assert page.status_code == 200
    assert [item["merchant_raw"] for item in page.json()["transactions"]] == ["Grab", "Coffee Bar"]
    assert too_large.status_code == 422
    assert too_large.json() == {"detail": "Invalid request payload."}


def test_invalid_filter_ranges_return_safe_error(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)

    invalid_dates = test_client.get(
        "/transactions?date_from=2026-02-01&date_to=2026-01-01",
        headers=auth_headers(user),
    )
    invalid_amounts = test_client.get("/transactions?min_amount=10&max_amount=1", headers=auth_headers(user))

    assert invalid_dates.status_code == 422
    assert invalid_dates.json() == {"detail": "Invalid request payload."}
    assert invalid_amounts.status_code == 422
    assert invalid_amounts.json() == {"detail": "Invalid request payload."}


def test_get_transaction_by_id_and_cross_user_access(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    other = register_user(test_client, "other-get@example.com")
    transactions = seed_transactions(session, user["user"]["id"])

    own_response = test_client.get(f"/transactions/{transactions[0].id}", headers=auth_headers(user))
    cross_user_response = test_client.get(f"/transactions/{transactions[0].id}", headers=auth_headers(other))

    assert own_response.status_code == 200
    assert own_response.json()["merchant_raw"] == "Netflix"
    assert cross_user_response.status_code == 404
    assert cross_user_response.json() == {"detail": "Transaction not found."}


def test_edit_category_and_audit_log(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    transactions = seed_transactions(session, user["user"]["id"])

    response = test_client.patch(
        f"/transactions/{transactions[0].id}/category",
        headers=auth_headers(user),
        json={"category": "entertainment"},
    )

    assert response.status_code == 200
    assert response.json()["category"] == "entertainment"
    updated = session.get(Transaction, transactions[0].id)
    assert updated is not None
    assert updated.category_manually_set is True
    audit_log = session.exec(select(AuditLog).where(AuditLog.action == "transaction.category_changed")).one()
    assert audit_log.metadata_json == {
        "transaction_id": str(transactions[0].id),
        "old_category": "subscriptions",
        "new_category": "entertainment",
    }


def test_reject_invalid_category_and_mass_assignment(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    transactions = seed_transactions(session, user["user"]["id"])

    invalid = test_client.patch(
        f"/transactions/{transactions[0].id}/category",
        headers=auth_headers(user),
        json={"category": "travel"},
    )
    mass_assignment = test_client.patch(
        f"/transactions/{transactions[0].id}/category",
        headers=auth_headers(user),
        json={"category": "food", "amount": "1.00", "user_id": user["user"]["id"]},
    )

    assert invalid.status_code == 422
    assert mass_assignment.status_code == 422
    session.refresh(transactions[0])
    assert transactions[0].category == "subscriptions"
    assert transactions[0].amount == Decimal("-549.00")


def test_prevent_cross_user_category_edit(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    other = register_user(test_client, "other-edit@example.com")
    transactions = seed_transactions(session, user["user"]["id"])

    response = test_client.patch(
        f"/transactions/{transactions[0].id}/category",
        headers=auth_headers(other),
        json={"category": "food"},
    )

    assert response.status_code == 404
    session.refresh(transactions[0])
    assert transactions[0].category == "subscriptions"


def test_category_summary_is_correct(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_transactions(session, user["user"]["id"])

    response = test_client.get("/transactions/categories/summary", headers=auth_headers(user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_expenses"] == "929.00"
    assert payload["total_income"] == "35000.00"
    assert payload["transaction_count"] == 4
    assert payload["items"][0] == {
        "category": "subscriptions",
        "total_amount": "549.00",
        "transaction_count": 1,
        "percentage_of_total_expenses": "59.10",
    }


def test_merchant_summary_is_correct(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user = register_user(test_client)
    seed_transactions(session, user["user"]["id"])

    response = test_client.get("/transactions/merchants/summary?category=transportation", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "merchant_normalized": "grab",
            "total_amount": "-230.00",
            "transaction_count": 1,
            "first_seen": "2026-01-08",
            "last_seen": "2026-01-08",
        }
    ]


def test_transaction_rate_limit_behavior(client) -> None:  # noqa: ANN001
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    client.dependency_overrides[get_transaction_rate_limiter] = lambda: limiter
    test_client = TestClient(client)
    user = register_user(test_client)

    first = test_client.get("/transactions", headers=auth_headers(user))
    second = test_client.get("/transactions", headers=auth_headers(user))

    assert first.status_code == 200
    assert second.status_code == 429
