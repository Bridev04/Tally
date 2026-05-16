from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.reports import get_report_rate_limiter
from app.core.config import get_settings
from app.core.rate_limit import InMemoryRateLimiter
from app.models import AuditLog, MonthlyInsightReport, SpendingAnomaly, Subscription, Transaction, TransactionUpload, User
from app.services.llm.fake import FakeMonthlySummaryLLM
from app.services.llm.schemas import MonthlySummaryInput
from app.services.monthly_reports import MonthlyReportService, is_safe_monthly_summary


def register_user(test_client: TestClient, email: str = "reports@example.com") -> dict:
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def current_user(session: Session, payload: dict) -> User:
    user = session.get(User, UUID(payload["user"]["id"]))
    assert user is not None
    return user


def seed_report_data(session: Session, user_id: str, merchant_prefix: str = "") -> None:
    upload = TransactionUpload(
        user_id=UUID(user_id),
        file_name=f"{merchant_prefix or 'report'}-seed.csv",
        upload_status="completed",
        total_rows=8,
        processed_rows=8,
    )
    session.add(upload)
    session.flush()
    rows = [
        (date(2026, 5, 1), "Payroll", "50000.00", "income", 0.99),
        (date(2026, 5, 2), "Supermart", "-3000.00", "food", 0.95),
        (date(2026, 5, 3), "Cafe", "-500.00", "food", 0.88),
        (date(2026, 5, 4), "Grab", "-700.00", "transportation", 0.93),
        (date(2026, 5, 5), "Netflix", "-549.00", "subscriptions", 0.91),
        (date(2026, 5, 6), "Unknown Shop", "-120.00", "needs_review", 0.30),
        (date(2026, 5, 7), "Low Confidence", "-200.00", "shopping", 0.40),
        (date(2026, 4, 1), "Old Store", "-999.00", "shopping", 0.95),
    ]
    for transaction_date, merchant, amount, category, confidence in rows:
        session.add(
            Transaction(
                user_id=UUID(user_id),
                upload_id=upload.id,
                transaction_date=transaction_date,
                merchant_raw=f"{merchant_prefix}{merchant}",
                merchant_normalized=f"{merchant_prefix}{merchant}".lower(),
                description="Sensitive imported memo",
                amount=Decimal(amount),
                currency="PHP",
                category=category,
                category_confidence=confidence,
                category_source="auto",
            )
        )
    session.add(
        Subscription(
            user_id=UUID(user_id),
            merchant_name=f"{merchant_prefix}Netflix",
            average_amount=Decimal("549.00"),
            frequency="monthly",
            first_seen=date(2026, 1, 1),
            last_seen=date(2026, 5, 1),
            next_expected_date=date(2026, 6, 1),
            confidence_score=0.95,
            status="active",
        )
    )
    session.add(
        Subscription(
            user_id=UUID(user_id),
            merchant_name=f"{merchant_prefix}Paused App",
            average_amount=Decimal("99.00"),
            frequency="monthly",
            first_seen=date(2026, 1, 1),
            last_seen=date(2026, 5, 1),
            next_expected_date=date(2026, 6, 1),
            confidence_score=0.90,
            status="paused",
        )
    )
    session.add(
        SpendingAnomaly(
            user_id=UUID(user_id),
            anomaly_type="CATEGORY_SPIKE",
            category="food",
            amount_delta=Decimal("1500.00"),
            percentage_change=60.0,
            explanation="Food spending changed compared with the previous month, based on imported transactions.",
            severity="high",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            created_at=datetime(2026, 5, 10, tzinfo=UTC),
        )
    )
    session.commit()


class UnsafeLLM:
    def generate_monthly_summary(self, summary_input: MonthlySummaryInput) -> str:
        del summary_input
        return "You should cancel this subscription and stop spending."


class CapturingLLM:
    def __init__(self) -> None:
        self.input: MonthlySummaryInput | None = None

    def generate_monthly_summary(self, summary_input: MonthlySummaryInput) -> str:
        self.input = summary_input
        return "Based on your imported transactions, this month shows categorized spending activity."


def test_report_generation_with_no_transactions_returns_safe_fallback(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user_payload = register_user(test_client, "reports-empty@example.com")

    report = MonthlyReportService().generate(
        session=session,
        current_user=current_user(session, user_payload),
        month="2026-05",
        settings=get_settings(),
        use_ai=False,
    )

    assert report.total_spend == Decimal("0.00")
    assert report.total_income == Decimal("0.00")
    assert report.transaction_count == 0
    assert "no transactions were found" in (report.ai_summary or "")
    assert "not financial advice" in (report.ai_summary or "").lower()


def test_report_generation_uses_current_user_data_and_calculates_sections(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    owner = register_user(test_client, "reports-owner@example.com")
    other = register_user(test_client, "reports-other@example.com")
    seed_report_data(session, owner["user"]["id"])
    seed_report_data(session, other["user"]["id"], merchant_prefix="Other ")

    report = MonthlyReportService().generate(
        session=session,
        current_user=current_user(session, owner),
        month="2026-05",
        settings=get_settings(),
        use_ai=False,
    )
    read = MonthlyReportService().to_read(report)

    assert read.total_income == Decimal("50000.00")
    assert read.total_expenses == Decimal("5069.00")
    assert read.net_flow == Decimal("44931.00")
    assert read.transaction_count == 7
    assert [item.category for item in read.top_categories] == ["food", "transportation", "subscriptions", "shopping", "needs_review"]
    assert read.top_categories[0].total_amount == Decimal("3500.00")
    assert read.detected_subscriptions[0].merchant_name == "Netflix"
    assert len(read.detected_subscriptions) == 1
    assert read.anomalies[0].anomaly_type == "CATEGORY_SPIKE"
    assert read.needs_review_count == 2
    assert read.largest_merchant_total is not None
    assert read.largest_merchant_total.merchant_name == "Supermart"
    assert "other" not in str(read).lower()
    assert "sensitive imported memo" not in str(read).lower()


def test_existing_report_returned_unless_force_refresh(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user_payload = register_user(test_client, "reports-refresh@example.com")
    seed_report_data(session, user_payload["user"]["id"])
    service = MonthlyReportService()
    user = current_user(session, user_payload)

    first = service.generate(session=session, current_user=user, month="2026-05", settings=get_settings(), use_ai=False)
    first_id = first.id
    first_count = first.transaction_count
    second = service.generate(session=session, current_user=user, month="2026-05", settings=get_settings(), use_ai=False)
    refreshed = service.generate(
        session=session,
        current_user=user,
        month="2026-05",
        settings=get_settings(),
        use_ai=False,
        force_refresh=True,
    )

    assert second.id == first_id
    assert second.transaction_count == first_count
    assert refreshed.id == first_id
    assert refreshed.updated_at >= first.updated_at


def test_ai_usage_accepts_safe_output_and_rejects_unsafe_output(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    safe_user = register_user(test_client, "reports-safe-ai@example.com")
    unsafe_user = register_user(test_client, "reports-unsafe-ai@example.com")
    seed_report_data(session, safe_user["user"]["id"])
    seed_report_data(session, unsafe_user["user"]["id"])
    service = MonthlyReportService()

    safe = service.generate(
        session=session,
        current_user=current_user(session, safe_user),
        month="2026-05",
        settings=get_settings(),
        use_ai=True,
        llm_client=FakeMonthlySummaryLLM(),
    )
    unsafe = service.generate(
        session=session,
        current_user=current_user(session, unsafe_user),
        month="2026-05",
        settings=get_settings(),
        use_ai=True,
        llm_client=UnsafeLLM(),
    )

    assert safe.generation_source == "llm"
    assert safe.safety_flags_json == []
    assert unsafe.generation_source == "llm_fallback"
    assert "unsafe_ai_summary_rejected" in unsafe.safety_flags_json
    assert "you should" not in (unsafe.ai_summary or "").lower()


def test_llm_prompt_input_uses_aggregated_data_only(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user_payload = register_user(test_client, "reports-capture-ai@example.com")
    seed_report_data(session, user_payload["user"]["id"])
    llm = CapturingLLM()

    MonthlyReportService().generate(
        session=session,
        current_user=current_user(session, user_payload),
        month="2026-05",
        settings=get_settings(),
        use_ai=True,
        llm_client=llm,
    )

    assert llm.input is not None
    serialized = llm.input.model_dump_json().lower()
    assert "sensitive imported memo" not in serialized
    assert "description" not in serialized
    assert "raw" not in serialized


def test_forbidden_advice_words_are_detected() -> None:
    assert is_safe_monthly_summary("Based on imported transactions, the largest category was food.")
    assert is_safe_monthly_summary("This is a neutral summary, not financial advice.")
    assert not is_safe_monthly_summary("You should cancel this subscription.")
    assert not is_safe_monthly_summary("Use this credit card for guaranteed profit.")


def test_report_routes_auth_privacy_validation_and_rate_limit(client, session: Session) -> None:  # noqa: ANN001
    limiter = InMemoryRateLimiter(limit=20, window_seconds=60)
    client.dependency_overrides[get_report_rate_limiter] = lambda: limiter
    test_client = TestClient(client)
    owner = register_user(test_client, "reports-route-owner@example.com")
    other = register_user(test_client, "reports-route-other@example.com")
    seed_report_data(session, owner["user"]["id"])
    seed_report_data(session, other["user"]["id"], merchant_prefix="Other ")

    unauthenticated = test_client.post("/reports/monthly/generate", json={"month": "2026-05"})
    invalid = test_client.post("/reports/monthly/generate", headers=auth_headers(owner), json={"month": "05-2026"})
    generated = test_client.post(
        "/reports/monthly/generate",
        headers=auth_headers(owner),
        json={"month": "2026-05", "use_ai": False},
    )
    report_id = generated.json()["id"]
    owner_list = test_client.get("/reports/monthly?month=2026-05", headers=auth_headers(owner))
    owner_read = test_client.get(f"/reports/monthly/{report_id}", headers=auth_headers(owner))
    other_read = test_client.get(f"/reports/monthly/{report_id}", headers=auth_headers(other))

    assert unauthenticated.status_code == 401
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "Invalid request payload."}
    assert generated.status_code == 200
    payload_text = str(generated.json()).lower()
    assert "sensitive imported memo" not in payload_text
    assert "traceback" not in invalid.text.lower()
    assert owner_list.json()["count"] == 1
    assert owner_read.status_code == 200
    assert other_read.status_code == 404


def test_report_route_rate_limit_behavior(client) -> None:  # noqa: ANN001
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    client.dependency_overrides[get_report_rate_limiter] = lambda: limiter
    test_client = TestClient(client)
    user = register_user(test_client, "reports-rate@example.com")

    first = test_client.get("/reports/monthly", headers=auth_headers(user))
    second = test_client.get("/reports/monthly", headers=auth_headers(user))

    assert first.status_code == 200
    assert second.status_code == 429


def test_use_ai_true_falls_back_when_llm_unavailable(client, session: Session) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    user_payload = register_user(test_client, "reports-no-llm@example.com")
    seed_report_data(session, user_payload["user"]["id"])

    report = MonthlyReportService().generate(
        session=session,
        current_user=current_user(session, user_payload),
        month="2026-05",
        settings=get_settings(),
        use_ai=True,
    )

    assert report.generation_source == "llm_fallback"
    assert "llm_unavailable" in report.safety_flags_json
    assert "not financial advice" in (report.ai_summary or "").lower()
    assert len(session.exec(select(AuditLog)).all()) >= 1
    assert len(session.exec(select(MonthlyInsightReport)).all()) == 1
