from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session

from app.models import MonthlyInsightReport, SpendingAnomaly, Subscription, Transaction, TransactionUpload


def create_upload(
    *,
    session: Session,
    user_id: UUID,
    file_name: str = "transactions.csv",
    source: str = "csv",
    is_demo: bool = False,
    demo_scenario: str | None = None,
) -> TransactionUpload:
    upload = TransactionUpload(
        user_id=user_id,
        file_name=file_name,
        upload_status="completed",
        total_rows=1,
        processed_rows=1,
        source=source,
        is_demo=is_demo,
        demo_scenario=demo_scenario,
    )
    session.add(upload)
    session.flush()
    return upload


def create_transaction(
    *,
    session: Session,
    user_id: UUID,
    upload_id: UUID,
    transaction_date: date = date(2026, 5, 1),
    merchant: str = "Coffee Bar",
    amount: Decimal = Decimal("-120.00"),
    category: str = "food",
    source: str = "csv",
    is_demo: bool = False,
    demo_scenario: str | None = None,
) -> Transaction:
    transaction = Transaction(
        user_id=user_id,
        upload_id=upload_id,
        transaction_date=transaction_date,
        merchant_raw=merchant,
        merchant_normalized=merchant.lower(),
        description="Synthetic test transaction",
        amount=amount,
        currency="PHP",
        category=category,
        category_source="imported",
        source=source,
        is_demo=is_demo,
        demo_scenario=demo_scenario,
    )
    session.add(transaction)
    session.flush()
    return transaction


def create_recurring_subscription(*, session: Session, user_id: UUID, merchant: str = "Netflix") -> Subscription:
    subscription = Subscription(
        user_id=user_id,
        merchant_name=merchant,
        average_amount=Decimal("549.00"),
        frequency="monthly",
        first_seen=date(2026, 3, 1),
        last_seen=date(2026, 5, 1),
        next_expected_date=date(2026, 6, 1),
        confidence_score=0.95,
        status="active",
    )
    session.add(subscription)
    session.flush()
    return subscription


def create_anomaly(*, session: Session, user_id: UUID) -> SpendingAnomaly:
    anomaly = SpendingAnomaly(
        user_id=user_id,
        anomaly_type="CATEGORY_SPIKE",
        category="food",
        amount_delta=Decimal("500.00"),
        explanation="Food spending changed compared with the baseline.",
        severity="medium",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
    )
    session.add(anomaly)
    session.flush()
    return anomaly


def create_monthly_report(*, session: Session, user_id: UUID) -> MonthlyInsightReport:
    report = MonthlyInsightReport(
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
        generation_source="deterministic",
        safety_flags_json=["not_financial_advice"],
    )
    session.add(report)
    session.flush()
    return report
