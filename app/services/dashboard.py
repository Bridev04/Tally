from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
import uuid

from sqlmodel import Session, select

from app.models import SpendingAnomaly, Subscription, Transaction, TransactionUpload
from app.schemas.dashboard import (
    AnomalyDashboardItem,
    AnomalyDashboardSummary,
    DashboardSummaryResponse,
    LatestUploadSummary,
    RecentTransactionItem,
    SubscriptionDashboardItem,
    SubscriptionDashboardSummary,
    TopCategoryItem,
)


EXCLUDED_EXPENSE_CATEGORIES = {"income", "transfer"}


class DashboardService:
    def summarize(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month: str | None,
        low_confidence_threshold: float,
    ) -> DashboardSummaryResponse:
        selected_month = month or self._latest_transaction_month(session=session, user_id=user_id)
        latest_upload = self._latest_upload(session=session, user_id=user_id)

        if selected_month is None:
            return self._empty_response(latest_upload=latest_upload)

        month_start, month_end = self._month_window(selected_month)
        transactions = session.exec(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date <= month_end,
            )
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        ).all()

        if not transactions:
            return self._empty_response(month=selected_month, latest_upload=latest_upload)

        total_income = self._money(sum((item.amount for item in transactions if item.amount > 0), Decimal("0")))
        total_expenses = self._money(sum((-item.amount for item in transactions if item.amount < 0), Decimal("0")))
        net_flow = self._money(total_income - total_expenses)
        currency = self._currency_for(transactions)

        return DashboardSummaryResponse(
            month=selected_month,
            currency=currency,
            total_income=total_income,
            total_expenses=total_expenses,
            net_flow=net_flow,
            transaction_count=len(transactions),
            top_categories=self._top_categories(transactions=transactions, total_expenses=total_expenses),
            recent_transactions=[
                RecentTransactionItem.model_validate(item)
                for item in sorted(transactions, key=lambda item: (item.transaction_date, item.created_at), reverse=True)[:5]
            ],
            subscription_summary=self._subscription_summary(session=session, user_id=user_id),
            anomaly_summary=self._anomaly_summary(
                session=session,
                user_id=user_id,
                month_start=month_start,
                month_end=month_end,
            ),
            needs_review_count=self._needs_review_count(
                transactions=transactions,
                low_confidence_threshold=low_confidence_threshold,
            ),
            latest_upload=latest_upload,
            has_data=True,
        )

    def _empty_response(
        self,
        *,
        month: str | None = None,
        latest_upload: LatestUploadSummary | None = None,
    ) -> DashboardSummaryResponse:
        return DashboardSummaryResponse(
            month=month,
            currency="PHP",
            total_income=Decimal("0.00"),
            total_expenses=Decimal("0.00"),
            net_flow=Decimal("0.00"),
            transaction_count=0,
            top_categories=[],
            recent_transactions=[],
            subscription_summary=SubscriptionDashboardSummary(
                active_count=0,
                estimated_monthly_total=Decimal("0.00"),
                upcoming_items=[],
            ),
            anomaly_summary=AnomalyDashboardSummary(
                total_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                latest_items=[],
            ),
            needs_review_count=0,
            latest_upload=latest_upload,
            has_data=False,
        )

    def _latest_transaction_month(self, *, session: Session, user_id: uuid.UUID) -> str | None:
        transaction = session.exec(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(1)
        ).first()
        if transaction is None:
            return None
        return transaction.transaction_date.strftime("%Y-%m")

    def _latest_upload(self, *, session: Session, user_id: uuid.UUID) -> LatestUploadSummary | None:
        upload = session.exec(
            select(TransactionUpload)
            .where(TransactionUpload.user_id == user_id)
            .order_by(TransactionUpload.created_at.desc())
            .limit(1)
        ).first()
        if upload is None:
            return None
        return LatestUploadSummary.model_validate(upload)

    def _top_categories(self, *, transactions: list[Transaction], total_expenses: Decimal) -> list[TopCategoryItem]:
        totals: dict[str, tuple[Decimal, int]] = {}
        for transaction in transactions:
            category = transaction.category or "needs_review"
            if transaction.amount >= 0 or category in EXCLUDED_EXPENSE_CATEGORIES:
                continue
            current_total, current_count = totals.get(category, (Decimal("0"), 0))
            totals[category] = (current_total + (-transaction.amount), current_count + 1)

        return [
            TopCategoryItem(
                category=category,
                total_amount=self._money(amount),
                transaction_count=count,
                percentage_of_total_expenses=self._percentage(amount, total_expenses),
            )
            for category, (amount, count) in sorted(totals.items(), key=lambda item: (-item[1][0], item[0]))[:5]
        ]

    def _subscription_summary(self, *, session: Session, user_id: uuid.UUID) -> SubscriptionDashboardSummary:
        active_subscriptions = session.exec(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status == "active")
            .order_by(Subscription.next_expected_date.asc(), Subscription.merchant_name.asc())
        ).all()
        return SubscriptionDashboardSummary(
            active_count=len(active_subscriptions),
            estimated_monthly_total=self._money(sum((item.average_amount for item in active_subscriptions), Decimal("0"))),
            upcoming_items=[
                SubscriptionDashboardItem.model_validate(item)
                for item in sorted(
                    active_subscriptions,
                    key=lambda item: (item.next_expected_date is None, item.next_expected_date or date.max, item.merchant_name),
                )[:3]
            ],
        )

    def _anomaly_summary(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month_start: date,
        month_end: date,
    ) -> AnomalyDashboardSummary:
        anomalies = session.exec(select(SpendingAnomaly).where(SpendingAnomaly.user_id == user_id)).all()
        matching = [item for item in anomalies if self._anomaly_in_month(item, month_start=month_start, month_end=month_end)]
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for anomaly in matching:
            severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1

        latest = sorted(matching, key=lambda item: item.created_at, reverse=True)[:3]
        return AnomalyDashboardSummary(
            total_count=len(matching),
            high_count=severity_counts["high"],
            medium_count=severity_counts["medium"],
            low_count=severity_counts["low"],
            latest_items=[AnomalyDashboardItem.model_validate(item) for item in latest],
        )

    def _needs_review_count(self, *, transactions: list[Transaction], low_confidence_threshold: float) -> int:
        return sum(
            1
            for transaction in transactions
            if transaction.category == "needs_review"
            or (
                transaction.category_confidence is not None
                and transaction.category_confidence < low_confidence_threshold
            )
        )

    def _anomaly_in_month(self, anomaly: SpendingAnomaly, *, month_start: date, month_end: date) -> bool:
        if anomaly.period_start is not None or anomaly.period_end is not None:
            period_start = anomaly.period_start or anomaly.period_end
            period_end = anomaly.period_end or anomaly.period_start
            return period_start <= month_end and period_end >= month_start

        created_start = datetime.combine(month_start, time.min, tzinfo=anomaly.created_at.tzinfo)
        created_end = datetime.combine(month_end, time.max, tzinfo=anomaly.created_at.tzinfo)
        return created_start <= anomaly.created_at <= created_end

    def _month_window(self, month: str) -> tuple[date, date]:
        year, month_number = (int(part) for part in month.split("-"))
        month_start = date(year, month_number, 1)
        if month_number == 12:
            month_end = date(year, 12, 31)
        else:
            month_end = date(year, month_number + 1, 1).replace(day=1)
            month_end = date.fromordinal(month_end.toordinal() - 1)
        return month_start, month_end

    def _currency_for(self, transactions: list[Transaction]) -> str:
        currencies = [item.currency for item in transactions if item.currency]
        if not currencies:
            return "PHP"
        return max(sorted(set(currencies)), key=currencies.count)

    def _money(self, value: Decimal | int | float) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _percentage(self, value: Decimal, total: Decimal) -> Decimal:
        if total == 0:
            return Decimal("0.00")
        return ((value / total) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

