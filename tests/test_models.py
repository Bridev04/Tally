from datetime import date
from decimal import Decimal

from sqlalchemy import inspect
from sqlmodel import SQLModel, Session, create_engine, select

from app.models import (
    AuditLog,
    MonthlyInsightReport,
    SpendingAnomaly,
    Subscription,
    Transaction,
    TransactionUpload,
    User,
)


def test_core_models_can_be_created() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(email="demo@example.com", password_hash="hashed-password")
        session.add(user)
        session.commit()
        session.refresh(user)

        upload = TransactionUpload(
            user_id=user.id,
            file_name="may-transactions.csv",
            upload_status="processed",
            total_rows=1,
            processed_rows=1,
        )
        session.add(upload)
        session.commit()
        session.refresh(upload)

        transaction = Transaction(
            user_id=user.id,
            upload_id=upload.id,
            transaction_date=date(2026, 5, 1),
            merchant_raw="ACME COFFEE 1234",
            merchant_normalized="acme coffee",
            description="Morning coffee",
            amount=Decimal("4.50"),
            currency="USD",
            category="food",
            category_confidence=0.92,
            payment_type="card",
            is_recurring_candidate=False,
        )
        subscription = Subscription(
            user_id=user.id,
            merchant_name="Example Streaming",
            average_amount=Decimal("12.99"),
            frequency="monthly",
            first_seen=date(2026, 1, 1),
            last_seen=date(2026, 5, 1),
            next_expected_date=date(2026, 6, 1),
            confidence_score=0.88,
            status="active",
        )
        anomaly = SpendingAnomaly(
            user_id=user.id,
            anomaly_type="category_spike",
            category="food",
            merchant_name="acme coffee",
            amount_delta=Decimal("25.00"),
            percentage_change=42.5,
            explanation="Food spending is higher than the prior month.",
            severity="medium",
        )
        report = MonthlyInsightReport(
            user_id=user.id,
            month=date(2026, 5, 1),
            total_spend=Decimal("150.25"),
            top_categories_json={"food": "75.25", "transport": "75.00"},
            detected_subscriptions_json=[{"merchant_name": "Example Streaming"}],
            anomalies_json=[{"anomaly_type": "category_spike"}],
            ai_summary="Neutral monthly spending summary.",
        )
        audit_log = AuditLog(
            user_id=user.id,
            action="transaction_upload.created",
            metadata_json={"file_name": "may-transactions.csv"},
        )

        session.add_all([transaction, subscription, anomaly, report, audit_log])
        session.commit()

        saved_user = session.exec(select(User).where(User.email == "demo@example.com")).one()
        assert saved_user.uploads[0].file_name == "may-transactions.csv"
        assert saved_user.transactions[0].merchant_normalized == "acme coffee"
        assert saved_user.subscriptions[0].merchant_name == "Example Streaming"
        assert saved_user.spending_anomalies[0].severity == "medium"
        assert saved_user.monthly_insight_reports[0].total_spend == Decimal("150.25")
        assert saved_user.audit_logs[0].action == "transaction_upload.created"


def test_required_indexes_exist() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)

    transaction_indexes = {
        index["name"] for index in inspector.get_indexes("transactions")
    }

    assert "ix_transactions_user_id" in transaction_indexes
    assert "ix_transactions_transaction_date" in transaction_indexes
    assert "ix_transactions_category" in transaction_indexes
    assert "ix_transactions_merchant_normalized" in transaction_indexes
