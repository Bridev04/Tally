from __future__ import annotations

from calendar import monthrange
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re
import uuid

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import SpendingAnomaly, Subscription, Transaction
from app.schemas.spending_anomaly import AnomalyFilterParams, AnomalyType, Severity
from app.schemas.transaction import TransactionCategory
from app.services.audit import create_audit_log
from app.services.transaction_import_utils import normalize_merchant


expense_excluded_categories = {
    TransactionCategory.income.value,
    TransactionCategory.transfer.value,
}

advice_words = {"cancel", "stop spending", "bad habit", "waste", "should"}


@dataclass(frozen=True)
class MonthWindow:
    start: date
    end: date
    label: str


@dataclass(frozen=True)
class AnomalyCandidate:
    anomaly_type: str
    explanation: str
    severity: str
    category: str | None = None
    merchant_name: str | None = None
    amount_delta: Decimal | None = None
    percentage_change: float | None = None
    transaction_count: int | None = None
    metadata_json: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AnomalyDetectionSummary:
    anomalies: list[SpendingAnomaly]
    detected_count: int
    month: str


class AnomalyDetectionService:
    minimum_category_total = Decimal("1000.00")
    minimum_category_delta = Decimal("500.00")
    category_spike_percentage = 40.0
    merchant_frequency_minimum_count = 5
    merchant_frequency_multiplier = 2
    merchant_frequency_delta = 3
    small_purchase_maximum = Decimal("300.00")
    small_purchase_minimum_count = 5
    small_purchase_total = Decimal("1000.00")
    subscription_change_percentage = 10.0
    subscription_change_delta = Decimal("20.00")
    low_confidence_cutoff = 0.60

    def detect_and_upsert(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month: str | None = None,
        force_refresh: bool = False,
        audit: bool = False,
    ) -> AnomalyDetectionSummary:
        window = self._target_month(session=session, user_id=user_id, month=month)
        baseline = self._previous_month(window.start)
        if force_refresh:
            existing_for_month = session.exec(
                select(SpendingAnomaly).where(
                    SpendingAnomaly.user_id == user_id,
                    SpendingAnomaly.period_start == window.start,
                    SpendingAnomaly.period_end == window.end,
                )
            ).all()
            for anomaly in existing_for_month:
                session.delete(anomaly)
            session.flush()

        candidates = self.detect(session=session, user_id=user_id, month=window)
        existing = self._existing_for_month(session=session, user_id=user_id, month=window)
        anomalies: list[SpendingAnomaly] = []
        for candidate in candidates:
            key = self._dedupe_key(candidate)
            anomaly = existing.get(key)
            if anomaly is None:
                anomaly = SpendingAnomaly(
                    user_id=user_id,
                    anomaly_type=candidate.anomaly_type,
                    category=candidate.category,
                    merchant_name=candidate.merchant_name,
                    period_start=window.start,
                    period_end=window.end,
                    baseline_period_start=baseline.start,
                    baseline_period_end=baseline.end,
                )
            anomaly.amount_delta = candidate.amount_delta
            anomaly.percentage_change = candidate.percentage_change
            anomaly.explanation = self._neutralize(candidate.explanation)
            anomaly.severity = candidate.severity
            anomaly.transaction_count = candidate.transaction_count
            anomaly.metadata_json = candidate.metadata_json
            session.add(anomaly)
            anomalies.append(anomaly)

        session.flush()
        for anomaly in anomalies:
            session.refresh(anomaly)

        if audit:
            create_audit_log(
                session=session,
                user_id=user_id,
                action="anomaly.detected",
                metadata={
                    "month": window.label,
                    "detected_count": len(anomalies),
                    "force_refresh": force_refresh,
                },
            )
            session.flush()

        return AnomalyDetectionSummary(
            anomalies=sorted(anomalies, key=lambda item: self._sort_key(item)),
            detected_count=len(anomalies),
            month=window.label,
        )

    def detect(self, *, session: Session, user_id: uuid.UUID, month: MonthWindow) -> list[AnomalyCandidate]:
        baseline = self._previous_month(month.start)
        current_transactions = self._transactions_for_window(session=session, user_id=user_id, window=month)
        baseline_transactions = self._transactions_for_window(session=session, user_id=user_id, window=baseline)
        candidates: list[AnomalyCandidate] = []
        candidates.extend(self._category_spikes(current_transactions, baseline_transactions))
        candidates.extend(self._merchant_frequency_spikes(current_transactions, baseline_transactions))
        candidates.extend(self._repeated_small_purchases(current_transactions))
        candidates.extend(self._subscription_price_changes(session, user_id, current_transactions))
        candidates.extend(self._duplicate_like_transactions(current_transactions))
        needs_review = self._needs_review_cluster(current_transactions)
        if needs_review is not None:
            candidates.append(needs_review)
        return sorted(candidates, key=lambda item: self._candidate_sort_key(item))

    def list_anomalies(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        filters: AnomalyFilterParams,
    ) -> list[SpendingAnomaly]:
        statement = select(SpendingAnomaly).where(SpendingAnomaly.user_id == user_id)
        if filters.month is not None:
            window = self._month_from_label(filters.month)
            statement = statement.where(SpendingAnomaly.period_start == window.start)
        if filters.severity is not None:
            statement = statement.where(SpendingAnomaly.severity == filters.severity.value)
        if filters.anomaly_type is not None:
            statement = statement.where(SpendingAnomaly.anomaly_type == filters.anomaly_type.value)
        return session.exec(
            statement.order_by(SpendingAnomaly.created_at.desc(), SpendingAnomaly.id.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        ).all()

    def summarize(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month: str | None = None,
    ) -> tuple[MonthWindow, list[SpendingAnomaly]]:
        window = self._target_month(session=session, user_id=user_id, month=month)
        anomalies = session.exec(
            select(SpendingAnomaly).where(
                SpendingAnomaly.user_id == user_id,
                SpendingAnomaly.period_start == window.start,
            )
        ).all()
        return window, anomalies

    def _category_spikes(
        self,
        current_transactions: list[Transaction],
        baseline_transactions: list[Transaction],
    ) -> list[AnomalyCandidate]:
        current_totals = self._expense_totals_by_category(current_transactions)
        baseline_totals = self._expense_totals_by_category(baseline_transactions)
        candidates: list[AnomalyCandidate] = []
        for category, current_total in current_totals.items():
            baseline_total = baseline_totals.get(category, Decimal("0.00"))
            if baseline_total <= 0 or current_total < self.minimum_category_total:
                continue
            amount_delta = self._money(current_total - baseline_total)
            percentage_change = self._percentage(amount_delta, baseline_total)
            if amount_delta < self.minimum_category_delta or percentage_change < self.category_spike_percentage:
                continue
            candidates.append(
                AnomalyCandidate(
                    anomaly_type=AnomalyType.category_spike.value,
                    category=category,
                    amount_delta=amount_delta,
                    percentage_change=percentage_change,
                    explanation=(
                        f"{self._label(category)} spending increased by {percentage_change:.0f}% "
                        "compared with the previous month, based on imported transactions."
                    ),
                    severity=self._severity(percentage_change=percentage_change, amount_delta=amount_delta),
                    transaction_count=sum(1 for item in current_transactions if self._category(item) == category),
                    metadata_json={
                        "current_total": str(self._money(current_total)),
                        "baseline_total": str(self._money(baseline_total)),
                    },
                )
            )
        return candidates

    def _merchant_frequency_spikes(
        self,
        current_transactions: list[Transaction],
        baseline_transactions: list[Transaction],
    ) -> list[AnomalyCandidate]:
        current_counts = self._expense_counts_by_merchant(current_transactions)
        baseline_counts = self._expense_counts_by_merchant(baseline_transactions)
        display_names = self._display_names_by_merchant(current_transactions)
        candidates: list[AnomalyCandidate] = []
        for merchant_key, current_count in current_counts.items():
            baseline_count = baseline_counts.get(merchant_key, 0)
            difference = current_count - baseline_count
            if (
                current_count < self.merchant_frequency_minimum_count
                or baseline_count <= 0
                or current_count < baseline_count * self.merchant_frequency_multiplier
                or difference < self.merchant_frequency_delta
            ):
                continue
            percentage_change = self._percentage(Decimal(difference), Decimal(baseline_count))
            merchant_name = display_names.get(merchant_key, merchant_key.title())
            candidates.append(
                AnomalyCandidate(
                    anomaly_type=AnomalyType.merchant_frequency_spike.value,
                    merchant_name=merchant_name,
                    amount_delta=Decimal(difference),
                    percentage_change=percentage_change,
                    explanation=(
                        f"{merchant_name} appeared {current_count} times this month compared with "
                        f"{baseline_count} times in the previous month."
                    ),
                    severity=Severity.medium.value if difference >= 6 else Severity.low.value,
                    transaction_count=current_count,
                    metadata_json={"baseline_count": baseline_count},
                )
            )
        return candidates

    def _repeated_small_purchases(self, transactions: list[Transaction]) -> list[AnomalyCandidate]:
        grouped: dict[str, list[Transaction]] = defaultdict(list)
        for transaction in transactions:
            if self._is_expense(transaction) and abs(transaction.amount) <= self.small_purchase_maximum:
                merchant_key = self._merchant_key(transaction)
                if merchant_key:
                    grouped[merchant_key].append(transaction)

        display_names = self._display_names_by_merchant(transactions)
        candidates: list[AnomalyCandidate] = []
        for merchant_key, items in grouped.items():
            total = self._money(sum((abs(item.amount) for item in items), Decimal("0.00")))
            if len(items) < self.small_purchase_minimum_count or total < self.small_purchase_total:
                continue
            merchant_name = display_names.get(merchant_key, merchant_key.title())
            candidates.append(
                AnomalyCandidate(
                    anomaly_type=AnomalyType.repeated_small_purchases.value,
                    merchant_name=merchant_name,
                    amount_delta=total,
                    explanation=(
                        f"Small purchases at {merchant_name} appeared {len(items)} times this month "
                        f"and totaled PHP {self._format_amount(total)}."
                    ),
                    severity=Severity.medium.value if total >= Decimal("2000.00") else Severity.low.value,
                    transaction_count=len(items),
                    metadata_json={"small_purchase_maximum": str(self.small_purchase_maximum)},
                )
            )
        return candidates

    def _subscription_price_changes(
        self,
        session: Session,
        user_id: uuid.UUID,
        transactions: list[Transaction],
    ) -> list[AnomalyCandidate]:
        subscriptions = session.exec(
            select(Subscription).where(Subscription.user_id == user_id, Subscription.status != "cancelled")
        ).all()
        by_merchant = {normalize_merchant(subscription.merchant_name): subscription for subscription in subscriptions}
        latest_by_merchant: dict[str, Transaction] = {}
        for transaction in sorted(transactions, key=lambda item: item.transaction_date):
            merchant_key = self._merchant_key(transaction)
            if merchant_key in by_merchant and self._is_expense(transaction):
                latest_by_merchant[merchant_key] = transaction

        candidates: list[AnomalyCandidate] = []
        for merchant_key, latest in latest_by_merchant.items():
            subscription = by_merchant[merchant_key]
            latest_amount = self._money(abs(latest.amount))
            average_amount = self._money(subscription.average_amount)
            if average_amount <= 0:
                continue
            amount_delta = self._money(latest_amount - average_amount)
            if abs(amount_delta) < self.subscription_change_delta:
                continue
            percentage_change = abs(self._percentage(amount_delta, average_amount))
            if percentage_change < self.subscription_change_percentage:
                continue
            merchant_name = subscription.merchant_name
            candidates.append(
                AnomalyCandidate(
                    anomaly_type=AnomalyType.subscription_price_change.value,
                    merchant_name=merchant_name,
                    amount_delta=amount_delta,
                    percentage_change=percentage_change,
                    explanation=(
                        f"{merchant_name}'s latest charge was PHP {self._format_amount(latest_amount)}, "
                        f"compared with the usual average of PHP {self._format_amount(average_amount)}."
                    ),
                    severity=self._severity(percentage_change=percentage_change, amount_delta=abs(amount_delta)),
                    transaction_count=1,
                    metadata_json={"subscription_id": str(subscription.id)},
                )
            )
        return candidates

    def _duplicate_like_transactions(self, transactions: list[Transaction]) -> list[AnomalyCandidate]:
        grouped: dict[tuple[date, str, Decimal, str], list[Transaction]] = defaultdict(list)
        for transaction in transactions:
            if not self._is_expense(transaction):
                continue
            merchant_key = self._merchant_key(transaction)
            description_key = self._description_key(transaction.description or transaction.merchant_raw)
            grouped[
                (
                    transaction.transaction_date,
                    merchant_key,
                    self._money(transaction.amount),
                    description_key,
                )
            ].append(transaction)

        display_names = self._display_names_by_merchant(transactions)
        candidates: list[AnomalyCandidate] = []
        for (transaction_date, merchant_key, amount, _description_key), items in grouped.items():
            if len(items) < 2:
                continue
            merchant_name = display_names.get(merchant_key, merchant_key.title())
            candidates.append(
                AnomalyCandidate(
                    anomaly_type=AnomalyType.duplicate_like_transactions.value,
                    merchant_name=merchant_name,
                    amount_delta=abs(amount),
                    explanation=(
                        f"{len(items)} similar transactions from {merchant_name} on the same date and amount "
                        "were found. This may be worth reviewing."
                    ),
                    severity=Severity.low.value,
                    transaction_count=len(items),
                    metadata_json={"transaction_date": transaction_date.isoformat()},
                )
            )
        return candidates

    def _needs_review_cluster(self, transactions: list[Transaction]) -> AnomalyCandidate | None:
        needs_review_count = sum(
            1 for transaction in transactions if transaction.category == TransactionCategory.needs_review.value
        )
        low_confidence_count = sum(
            1
            for transaction in transactions
            if transaction.category_confidence is not None and transaction.category_confidence < self.low_confidence_cutoff
        )
        if needs_review_count < 5 and low_confidence_count < 10:
            return None
        total_count = max(needs_review_count, low_confidence_count)
        return AnomalyCandidate(
            anomaly_type=AnomalyType.needs_review_cluster.value,
            category=TransactionCategory.needs_review.value,
            explanation="Several transactions have low categorization confidence and may affect spending summaries.",
            severity=Severity.low.value,
            transaction_count=total_count,
            metadata_json={
                "needs_review_count": needs_review_count,
                "low_confidence_count": low_confidence_count,
            },
        )

    def _transactions_for_window(self, *, session: Session, user_id: uuid.UUID, window: MonthWindow) -> list[Transaction]:
        return session.exec(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= window.start,
                Transaction.transaction_date <= window.end,
            )
            .order_by(Transaction.transaction_date.asc(), Transaction.merchant_normalized.asc())
        ).all()

    def _target_month(self, *, session: Session, user_id: uuid.UUID, month: str | None) -> MonthWindow:
        if month is not None:
            return self._month_from_label(month)
        latest_date = session.exec(
            select(func.max(Transaction.transaction_date)).where(Transaction.user_id == user_id)
        ).one_or_none()
        if latest_date is None:
            today = date.today()
            return self._month_from_label(f"{today.year:04d}-{today.month:02d}")
        return self._month_from_label(f"{latest_date.year:04d}-{latest_date.month:02d}")

    def _month_from_label(self, label: str) -> MonthWindow:
        year, month = (int(part) for part in label.split("-", 1))
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        return MonthWindow(start=start, end=end, label=label)

    def _previous_month(self, value: date) -> MonthWindow:
        year = value.year
        month = value.month - 1
        if month == 0:
            year -= 1
            month = 12
        return self._month_from_label(f"{year:04d}-{month:02d}")

    def _existing_for_month(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month: MonthWindow,
    ) -> dict[tuple[str, str | None, str | None], SpendingAnomaly]:
        anomalies = session.exec(
            select(SpendingAnomaly).where(
                SpendingAnomaly.user_id == user_id,
                SpendingAnomaly.period_start == month.start,
                SpendingAnomaly.period_end == month.end,
            )
        ).all()
        return {
            (
                anomaly.anomaly_type,
                anomaly.category,
                self._merchant_identity(anomaly.merchant_name),
            ): anomaly
            for anomaly in anomalies
        }

    def _dedupe_key(self, candidate: AnomalyCandidate) -> tuple[str, str | None, str | None]:
        return (
            candidate.anomaly_type,
            candidate.category,
            self._merchant_identity(candidate.merchant_name),
        )

    def _sort_key(self, anomaly: SpendingAnomaly) -> tuple[int, str, str, str]:
        return (
            self._severity_rank(anomaly.severity),
            anomaly.anomaly_type,
            anomaly.category or "",
            anomaly.merchant_name or "",
        )

    def _candidate_sort_key(self, candidate: AnomalyCandidate) -> tuple[int, str, str, str]:
        return (
            self._severity_rank(candidate.severity),
            candidate.anomaly_type,
            candidate.category or "",
            candidate.merchant_name or "",
        )

    def _severity_rank(self, severity: str) -> int:
        return {Severity.high.value: 0, Severity.medium.value: 1, Severity.low.value: 2}.get(severity, 3)

    def _severity(self, *, percentage_change: float, amount_delta: Decimal) -> str:
        if percentage_change >= 100 and amount_delta >= Decimal("2000.00"):
            return Severity.high.value
        if percentage_change >= 40 and amount_delta >= Decimal("500.00"):
            return Severity.medium.value
        return Severity.low.value

    def _expense_totals_by_category(self, transactions: list[Transaction]) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for transaction in transactions:
            if self._is_expense(transaction):
                totals[self._category(transaction)] += abs(transaction.amount)
        return totals

    def _expense_counts_by_merchant(self, transactions: list[Transaction]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for transaction in transactions:
            if self._is_expense(transaction):
                merchant_key = self._merchant_key(transaction)
                if merchant_key:
                    counts[merchant_key] += 1
        return counts

    def _display_names_by_merchant(self, transactions: list[Transaction]) -> dict[str, str]:
        names: dict[str, list[str]] = defaultdict(list)
        for transaction in transactions:
            merchant_key = self._merchant_key(transaction)
            if merchant_key and transaction.merchant_raw.strip():
                names[merchant_key].append(transaction.merchant_raw.strip())
        return {merchant_key: Counter(values).most_common(1)[0][0][:255] for merchant_key, values in names.items()}

    def _is_expense(self, transaction: Transaction) -> bool:
        return transaction.amount < 0 and self._category(transaction) not in expense_excluded_categories

    def _category(self, transaction: Transaction) -> str:
        return transaction.category or TransactionCategory.needs_review.value

    def _merchant_key(self, transaction: Transaction) -> str:
        return normalize_merchant(transaction.merchant_normalized or transaction.merchant_raw or "")

    def _merchant_identity(self, merchant_name: str | None) -> str | None:
        if merchant_name is None:
            return None
        return normalize_merchant(merchant_name)

    def _description_key(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def _percentage(self, delta: Decimal, baseline: Decimal) -> float:
        if baseline == 0:
            return 0.0
        return round(float((delta / baseline) * Decimal("100")), 1)

    def _money(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _format_amount(self, value: Decimal) -> str:
        return f"{value:,.2f}"

    def _label(self, value: str) -> str:
        return value.replace("_", " ").title()

    def _neutralize(self, explanation: str) -> str:
        lowered = explanation.lower()
        if any(word in lowered for word in advice_words):
            return "A spending pattern changed in the imported transactions. This may be worth reviewing."
        return explanation
