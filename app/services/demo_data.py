from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.config import Settings
from app.models import MonthlyInsightReport, SpendingAnomaly, Subscription, Transaction, TransactionUpload, User
from app.services.anomalies import AnomalyDetectionService
from app.services.monthly_reports import MonthlyReportService
from app.services.subscription_detection import SubscriptionDetectionService
from app.services.transaction_categorizer import TransactionCategorizerService
from app.services.transaction_import_utils import (
    build_transaction,
    create_upload_batch,
    find_duplicate_transaction,
    normalize_merchant,
)


DEMO_UPLOAD_FILE_NAME = "synthetic-demo-data"
DEFAULT_DEMO_SCENARIO = "full_portfolio"
ALLOWED_DEMO_SCENARIOS = ("basic", "subscriptions", "budget_leaks", "needs_review", "full_portfolio")


@dataclass(frozen=True)
class DemoScenarioInfo:
    key: str
    title: str
    description: str


@dataclass(frozen=True)
class DemoLoadResult:
    upload: TransactionUpload | None
    scenario: str
    total_rows: int
    processed_rows: int
    duplicate_rows: int
    uploads_created: int
    subscriptions_detected: int
    anomalies_detected: int
    reports_generated: int
    reset_existing_demo: bool
    run_processing: bool


DEMO_SCENARIOS = {
    "basic": DemoScenarioInfo(
        key="basic",
        title="Basic Demo",
        description="Normal dashboard, transactions, income, categories, and recent activity.",
    ),
    "subscriptions": DemoScenarioInfo(
        key="subscriptions",
        title="Subscription Creep",
        description="Recurring subscriptions, including one recurring charge that changes over time.",
    ),
    "budget_leaks": DemoScenarioInfo(
        key="budget_leaks",
        title="Budget Leaks",
        description="Synthetic patterns for category changes, frequency spikes, small purchases, and duplicate-like rows.",
    ),
    "needs_review": DemoScenarioInfo(
        key="needs_review",
        title="Needs Review",
        description="Ambiguous imported rows that demonstrate low-confidence categorization review.",
    ),
    "full_portfolio": DemoScenarioInfo(
        key="full_portfolio",
        title="Full Portfolio Demo",
        description="Three months of synthetic data for screenshots, walkthroughs, reports, and privacy controls.",
    ),
}


def txn(
    transaction_date: date,
    merchant: str,
    description: str,
    amount: str,
    *,
    category: str | None = None,
) -> dict:
    item = {
        "transaction_date": transaction_date,
        "merchant_raw": merchant,
        "description": description,
        "amount": Decimal(amount),
        "currency": "PHP",
    }
    if category is not None:
        item["category"] = category
        item["category_source"] = "imported"
    return item


basic_transactions = [
    txn(date(2026, 5, 1), "Company Payroll", "Synthetic monthly payroll", "35000.00"),
    txn(date(2026, 5, 2), "Meralco", "Synthetic electric bill", "-3100.00"),
    txn(date(2026, 5, 3), "Netflix", "Netflix monthly subscription", "-549.00"),
    txn(date(2026, 5, 5), "Spotify", "Spotify Premium", "-149.00"),
    txn(date(2026, 5, 6), "Grab", "Grab ride", "-210.00"),
    txn(date(2026, 5, 7), "Jollibee", "Meal", "-245.00"),
    txn(date(2026, 5, 8), "Shopee", "Synthetic online shopping", "-1290.00"),
    txn(date(2026, 5, 9), "Mercury Drug", "Pharmacy items", "-420.00"),
    txn(date(2026, 5, 10), "Globe", "Mobile plan", "-999.00"),
    txn(date(2026, 5, 11), "Foodpanda", "Food delivery", "-365.00"),
]


subscription_transactions = [
    *[
        txn(date(2026, month, 1), "Netflix", "Netflix monthly subscription", "-549.00")
        for month in (3, 4, 5)
    ],
    *[
        txn(date(2026, month, 5), "Spotify", "Spotify Premium", "-149.00")
        for month in (3, 4, 5)
    ],
    *[
        txn(date(2026, month, 9), "Canva", "Canva Pro subscription", "-299.00")
        for month in (3, 4, 5)
    ],
    txn(date(2026, 3, 14), "YouTube Premium", "YouTube Premium subscription", "-159.00"),
    txn(date(2026, 4, 14), "YouTube Premium", "YouTube Premium subscription", "-159.00"),
    txn(date(2026, 5, 14), "YouTube Premium", "YouTube Premium subscription", "-199.00"),
    *[
        txn(date(2026, month, 18), "Apple iCloud", "Apple iCloud storage", "-49.00")
        for month in (3, 4, 5)
    ],
    *[
        txn(date(2026, month, 22), "Google One", "Google One storage", "-89.00")
        for month in (3, 4, 5)
    ],
]


budget_leak_transactions = [
    txn(date(2026, 4, 1), "Company Payroll", "Synthetic monthly payroll", "35000.00"),
    txn(date(2026, 5, 1), "Company Payroll", "Synthetic monthly payroll", "35000.00"),
    txn(date(2026, 4, 3), "Foodpanda", "Food delivery", "-380.00"),
    txn(date(2026, 4, 12), "Foodpanda", "Food delivery", "-410.00"),
    txn(date(2026, 4, 20), "Foodpanda", "Food delivery", "-390.00"),
    txn(date(2026, 4, 8), "Starbucks", "Coffee", "-180.00"),
    txn(date(2026, 4, 22), "Starbucks", "Coffee", "-175.00"),
    *[
        txn(date(2026, 5, day), "Foodpanda", "Food delivery", "-455.00")
        for day in (2, 4, 6, 8, 10, 12, 14, 16)
    ],
    *[
        txn(date(2026, 5, day), "Starbucks", "Coffee", "-185.00")
        for day in (3, 5, 7, 9, 11, 13, 15)
    ],
    txn(date(2026, 5, 18), "Jollibee", "Meal", "-325.00"),
    txn(date(2026, 5, 19), "Jollibee", "Meal", "-355.00"),
    txn(date(2026, 5, 20), "Shopee", "Synthetic checkout", "-1290.00"),
    txn(date(2026, 5, 20), "Shopee", "synthetic checkout", "-1290.00"),
]


needs_review_transactions = [
    txn(date(2026, 5, 2), "Blue Note 12X", "Imported row needs review", "-215.00"),
    txn(date(2026, 5, 3), "Packet REF 71", "Imported row needs review", "-640.00"),
    txn(date(2026, 5, 4), "Campus Kiosk B", "Imported row needs review", "-120.00"),
    txn(date(2026, 5, 5), "MNL POS 8842", "Imported row needs review", "-810.00"),
    txn(date(2026, 5, 6), "Green Shelf", "Imported row needs review", "-275.00"),
    txn(date(2026, 5, 7), "River Desk", "Imported row needs review", "-395.00"),
]


full_portfolio_transactions = [
    *[
        txn(date(2026, month, 1), "Company Payroll", "Synthetic monthly payroll", "35000.00")
        for month in (3, 4, 5)
    ],
    *subscription_transactions,
    txn(date(2026, 3, 3), "Meralco", "Synthetic electric bill", "-2980.00"),
    txn(date(2026, 4, 3), "Meralco", "Synthetic electric bill", "-3060.00"),
    txn(date(2026, 5, 3), "Meralco", "Synthetic electric bill", "-3180.00"),
    txn(date(2026, 3, 4), "Globe", "Mobile plan", "-999.00"),
    txn(date(2026, 4, 4), "Globe", "Mobile plan", "-999.00"),
    txn(date(2026, 5, 4), "Globe", "Mobile plan", "-999.00"),
    txn(date(2026, 3, 6), "Grab", "Grab ride", "-190.00"),
    txn(date(2026, 3, 17), "Grab", "Grab ride", "-210.00"),
    txn(date(2026, 4, 6), "Grab", "Grab ride", "-175.00"),
    txn(date(2026, 4, 17), "Grab", "Grab ride", "-205.00"),
    txn(date(2026, 5, 6), "Grab", "Grab ride", "-220.00"),
    txn(date(2026, 5, 17), "Grab", "Grab ride", "-235.00"),
    txn(date(2026, 3, 8), "Jollibee", "Meal", "-220.00"),
    txn(date(2026, 4, 10), "Mercury Drug", "Pharmacy items", "-430.00"),
    txn(date(2026, 5, 12), "Lazada", "Synthetic online shopping", "-1890.00"),
    txn(date(2026, 5, 16), "Shopee", "Synthetic online shopping", "-1390.00"),
    *budget_leak_transactions[2:],
    *needs_review_transactions,
]


scenario_transactions = {
    "basic": basic_transactions,
    "subscriptions": subscription_transactions,
    "budget_leaks": budget_leak_transactions,
    "needs_review": needs_review_transactions,
    "full_portfolio": full_portfolio_transactions,
}

# Backward-compatible import used by older tests.
synthetic_transactions = full_portfolio_transactions


class DemoDataService:
    def scenarios(self) -> list[DemoScenarioInfo]:
        return [DEMO_SCENARIOS[key] for key in ALLOWED_DEMO_SCENARIOS]

    def load(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        scenario: str = DEFAULT_DEMO_SCENARIO,
        reset_existing_demo: bool = False,
        run_processing: bool = True,
        current_user: User | None = None,
        settings: Settings | None = None,
    ) -> DemoLoadResult:
        self._validate_scenario(scenario)
        if reset_existing_demo:
            self.clear_demo_records(session=session, user_id=user_id)

        rows = scenario_transactions[scenario]
        upload = create_upload_batch(
            session=session,
            user_id=user_id,
            file_name=DEMO_UPLOAD_FILE_NAME,
            total_rows=len(rows),
            source="demo",
            is_demo=True,
            demo_scenario=scenario,
        )

        processed_rows = 0
        duplicate_rows = 0
        for item in rows:
            merchant_normalized = normalize_merchant(item["merchant_raw"])
            duplicate = find_duplicate_transaction(
                session=session,
                user_id=user_id,
                transaction_date=item["transaction_date"],
                merchant_normalized=merchant_normalized,
                amount=item["amount"],
                description=item["description"],
            )
            if duplicate is not None:
                duplicate_rows += 1
                continue

            session.add(
                build_transaction(
                    user_id=user_id,
                    upload_id=upload.id,
                    merchant_normalized=merchant_normalized,
                    source="demo",
                    is_demo=True,
                    demo_scenario=scenario,
                    **item,
                )
            )
            processed_rows += 1

        upload.processed_rows = processed_rows
        upload.upload_status = "completed"
        session.flush()

        subscriptions_detected = 0
        anomalies_detected = 0
        reports_generated = 0
        if run_processing:
            subscriptions_detected, anomalies_detected, reports_generated = self.run_processing(
                session=session,
                user_id=user_id,
                current_user=current_user,
                settings=settings,
            )

        return DemoLoadResult(
            upload=upload,
            scenario=scenario,
            total_rows=upload.total_rows,
            processed_rows=processed_rows,
            duplicate_rows=duplicate_rows,
            uploads_created=1,
            subscriptions_detected=subscriptions_detected,
            anomalies_detected=anomalies_detected,
            reports_generated=reports_generated,
            reset_existing_demo=reset_existing_demo,
            run_processing=run_processing,
        )

    def reset(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        scenario: str | None,
        run_processing: bool,
        current_user: User | None = None,
        settings: Settings | None = None,
    ) -> DemoLoadResult:
        self.clear_demo_records(session=session, user_id=user_id)
        if scenario is None:
            return DemoLoadResult(
                upload=None,
                scenario=DEFAULT_DEMO_SCENARIO,
                total_rows=0,
                processed_rows=0,
                duplicate_rows=0,
                uploads_created=0,
                subscriptions_detected=0,
                anomalies_detected=0,
                reports_generated=0,
                reset_existing_demo=True,
                run_processing=False,
            )
        return self.load(
            session=session,
            user_id=user_id,
            scenario=scenario,
            reset_existing_demo=False,
            run_processing=run_processing,
            current_user=current_user,
            settings=settings,
        )

    def clear_demo_records(self, *, session: Session, user_id: uuid.UUID) -> None:
        demo_uploads = self._demo_uploads(session=session, user_id=user_id)
        upload_ids = [upload.id for upload in demo_uploads]
        demo_transactions = session.exec(
            select(Transaction).where(
                Transaction.user_id == user_id,
                or_(Transaction.is_demo.is_(True), Transaction.upload_id.in_(upload_ids)),
            )
        ).all()
        for transaction in demo_transactions:
            session.delete(transaction)
        session.flush()

        for upload in demo_uploads:
            session.delete(upload)
        self._clear_derived_records(session=session, user_id=user_id)
        session.flush()

    def run_processing(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        current_user: User | None,
        settings: Settings | None,
    ) -> tuple[int, int, int]:
        TransactionCategorizerService().categorize_user_transactions(
            session=session,
            user_id=user_id,
            force=True,
            overwrite_manual=False,
        )
        latest_date = self._latest_transaction_date(session=session, user_id=user_id)
        subscription_summary = SubscriptionDetectionService().detect_and_upsert(
            session=session,
            user_id=user_id,
            as_of=latest_date,
            audit=True,
        )
        anomaly_summary = AnomalyDetectionService().detect_and_upsert(
            session=session,
            user_id=user_id,
            force_refresh=True,
            audit=True,
        )
        reports_generated = 0
        if current_user is not None and settings is not None and latest_date is not None:
            MonthlyReportService().generate(
                session=session,
                current_user=current_user,
                month=f"{latest_date.year:04d}-{latest_date.month:02d}",
                settings=settings,
                use_ai=False,
                force_refresh=True,
            )
            reports_generated = 1
        return subscription_summary.detected_count, anomaly_summary.detected_count, reports_generated

    def _validate_scenario(self, scenario: str) -> None:
        if scenario not in scenario_transactions:
            raise ValueError("Invalid demo scenario.")

    def _demo_uploads(self, *, session: Session, user_id: uuid.UUID) -> list[TransactionUpload]:
        return session.exec(
            select(TransactionUpload).where(
                TransactionUpload.user_id == user_id,
                or_(TransactionUpload.is_demo.is_(True), TransactionUpload.file_name == DEMO_UPLOAD_FILE_NAME),
            )
        ).all()

    def _clear_derived_records(self, *, session: Session, user_id: uuid.UUID) -> None:
        for model in (Subscription, SpendingAnomaly, MonthlyInsightReport):
            records = session.exec(select(model).where(model.user_id == user_id)).all()
            for record in records:
                session.delete(record)

    def _latest_transaction_date(self, *, session: Session, user_id: uuid.UUID) -> date | None:
        return session.exec(select(func.max(Transaction.transaction_date)).where(Transaction.user_id == user_id)).one()
