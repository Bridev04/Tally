from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import statistics
import uuid

from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from app.models import AuditLog, Subscription, Transaction
from app.schemas.subscription import SubscriptionFilterParams
from app.schemas.transaction import TransactionCategory
from app.services.audit import create_audit_log
from app.services.transaction_categorizer import exact_merchant_categories
from app.services.transaction_import_utils import normalize_merchant


excluded_categories = {
    TransactionCategory.income.value,
    TransactionCategory.transfer.value,
}


@dataclass(frozen=True)
class RecurrenceCandidate:
    merchant_key: str
    merchant_name: str
    average_amount: Decimal
    frequency: str
    first_seen: date
    last_seen: date
    next_expected_date: date
    confidence_score: float
    status: str


@dataclass(frozen=True)
class DetectionSummary:
    subscriptions: list[Subscription]
    detected_count: int
    updated_count: int


class SubscriptionDetectionService:
    minimum_confidence = 0.72
    cadence_rules = {
        "weekly": {"target": 7, "tolerance": 2, "minimum_count": 3, "grace": 3, "pause": 14},
        "biweekly": {"target": 14, "tolerance": 2, "minimum_count": 3, "grace": 5, "pause": 28},
        "monthly": {"target": 30, "tolerance": 4, "minimum_count": 3, "grace": 7, "pause": 45},
        "yearly": {"target": 365, "tolerance": 15, "minimum_count": 2, "grace": 30, "pause": 90},
    }

    def detect_and_upsert(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        as_of: date | None = None,
        audit: bool = False,
    ) -> DetectionSummary:
        today = as_of or date.today()
        candidates = self.detect(session=session, user_id=user_id, as_of=today)
        existing = self._existing_by_merchant_key(session=session, user_id=user_id)
        manually_statused_ids = self._manual_status_subscription_ids(session=session, user_id=user_id)
        subscriptions: list[Subscription] = []
        updated_count = 0

        for candidate in candidates:
            subscription = existing.get(candidate.merchant_key)
            if subscription is None:
                subscription = Subscription(
                    user_id=user_id,
                    merchant_name=candidate.merchant_name,
                    average_amount=candidate.average_amount,
                    frequency=candidate.frequency,
                    first_seen=candidate.first_seen,
                    last_seen=candidate.last_seen,
                    next_expected_date=candidate.next_expected_date,
                    confidence_score=candidate.confidence_score,
                    status=candidate.status,
                )
            else:
                updated_count += 1
                subscription.merchant_name = candidate.merchant_name
                subscription.average_amount = candidate.average_amount
                subscription.frequency = candidate.frequency
                subscription.first_seen = candidate.first_seen
                subscription.last_seen = candidate.last_seen
                subscription.next_expected_date = candidate.next_expected_date
                subscription.confidence_score = candidate.confidence_score
                if subscription.id not in manually_statused_ids:
                    subscription.status = candidate.status

            session.add(subscription)
            subscriptions.append(subscription)

        session.flush()
        for subscription in subscriptions:
            session.refresh(subscription)

        if audit:
            create_audit_log(
                session=session,
                user_id=user_id,
                action="subscription.detected",
                metadata={
                    "detected_count": len(subscriptions),
                    "updated_count": updated_count,
                },
            )
            session.flush()

        return DetectionSummary(
            subscriptions=subscriptions,
            detected_count=len(subscriptions),
            updated_count=updated_count,
        )

    def detect(self, *, session: Session, user_id: uuid.UUID, as_of: date | None = None) -> list[RecurrenceCandidate]:
        today = as_of or date.today()
        transactions = session.exec(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.amount < 0,
                or_(Transaction.category.is_(None), Transaction.category.notin_(excluded_categories)),
            )
            .order_by(Transaction.merchant_normalized.asc(), Transaction.transaction_date.asc())
        ).all()

        grouped: dict[str, list[Transaction]] = defaultdict(list)
        for transaction in transactions:
            merchant_key = self._merchant_key(transaction)
            if merchant_key:
                grouped[merchant_key].append(transaction)

        candidates = [
            candidate
            for merchant_key, merchant_transactions in grouped.items()
            if (candidate := self._detect_group(merchant_key, merchant_transactions, today)) is not None
        ]
        return sorted(candidates, key=lambda item: (-item.confidence_score, item.merchant_name.lower()))

    def list_subscriptions(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        filters: SubscriptionFilterParams,
    ) -> list[Subscription]:
        statement = select(Subscription).where(Subscription.user_id == user_id)
        if filters.status is not None:
            statement = statement.where(Subscription.status == filters.status.value)
        if filters.frequency is not None:
            statement = statement.where(Subscription.frequency == filters.frequency.value)
        if filters.search is not None:
            search = filters.search.strip().lower()
            statement = statement.where(func.lower(Subscription.merchant_name).contains(search))

        status_rank = case(
            (Subscription.status == "active", 0),
            (Subscription.status == "paused", 1),
            (Subscription.status == "cancelled", 2),
            else_=3,
        )
        return session.exec(
            statement.order_by(
                status_rank.asc(),
                Subscription.next_expected_date.asc().nulls_last(),
                Subscription.confidence_score.desc(),
                Subscription.merchant_name.asc(),
            )
            .limit(filters.limit)
            .offset(filters.offset)
        ).all()

    def get_subscription(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        subscription_id: uuid.UUID,
    ) -> Subscription | None:
        return session.exec(
            select(Subscription).where(
                Subscription.id == subscription_id,
                Subscription.user_id == user_id,
            )
        ).first()

    def update_status(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        subscription_id: uuid.UUID,
        status: str,
    ) -> Subscription | None:
        subscription = self.get_subscription(
            session=session,
            user_id=user_id,
            subscription_id=subscription_id,
        )
        if subscription is None:
            return None

        old_status = subscription.status
        subscription.status = status
        session.add(subscription)
        create_audit_log(
            session=session,
            user_id=user_id,
            action="subscription.status_changed",
            metadata={
                "subscription_id": str(subscription.id),
                "old_status": old_status,
                "new_status": status,
            },
        )
        session.flush()
        session.refresh(subscription)
        return subscription

    def _detect_group(
        self,
        merchant_key: str,
        transactions: list[Transaction],
        as_of: date,
    ) -> RecurrenceCandidate | None:
        sorted_transactions = sorted(transactions, key=lambda item: item.transaction_date)
        if len(sorted_transactions) < 2:
            return None

        intervals = [
            (current.transaction_date - previous.transaction_date).days
            for previous, current in zip(sorted_transactions, sorted_transactions[1:])
            if current.transaction_date > previous.transaction_date
        ]
        if not intervals:
            return None

        amounts = [abs(transaction.amount) for transaction in sorted_transactions]
        average_amount = self._average_amount(amounts)
        amount_consistency = self._amount_consistency(amounts, average_amount)
        category_score = self._category_score(sorted_transactions)
        known_subscription_score = self._known_subscription_score(merchant_key)

        best: tuple[str, float, float] | None = None
        for frequency, rule in self.cadence_rules.items():
            if len(sorted_transactions) < int(rule["minimum_count"]):
                continue
            interval_consistency = self._interval_consistency(
                frequency=frequency,
                intervals=intervals,
            )
            if interval_consistency < 0.80:
                continue

            occurrence_score = self._occurrence_score(frequency=frequency, count=len(sorted_transactions))
            confidence = self._confidence(
                occurrence_score=occurrence_score,
                amount_consistency=amount_consistency,
                interval_consistency=interval_consistency,
                category_score=category_score,
                known_subscription_score=known_subscription_score,
            )
            if best is None or confidence > best[1]:
                best = (frequency, confidence, interval_consistency)

        if best is None:
            return None

        frequency, confidence, _interval_consistency = best
        if confidence < self.minimum_confidence or amount_consistency < 0.55:
            return None

        first_seen = sorted_transactions[0].transaction_date
        last_seen = sorted_transactions[-1].transaction_date
        next_expected_date = self._next_expected_date(last_seen=last_seen, frequency=frequency, intervals=intervals)
        return RecurrenceCandidate(
            merchant_key=merchant_key,
            merchant_name=self._display_merchant_name(merchant_key, sorted_transactions),
            average_amount=average_amount,
            frequency=frequency,
            first_seen=first_seen,
            last_seen=last_seen,
            next_expected_date=next_expected_date,
            confidence_score=round(confidence, 2),
            status=self._status(
                frequency=frequency,
                next_expected_date=next_expected_date,
                as_of=as_of,
            ),
        )

    def _existing_by_merchant_key(self, *, session: Session, user_id: uuid.UUID) -> dict[str, Subscription]:
        subscriptions = session.exec(select(Subscription).where(Subscription.user_id == user_id)).all()
        return {normalize_merchant(subscription.merchant_name): subscription for subscription in subscriptions}

    def _manual_status_subscription_ids(self, *, session: Session, user_id: uuid.UUID) -> set[uuid.UUID]:
        audit_logs = session.exec(
            select(AuditLog).where(
                AuditLog.user_id == user_id,
                AuditLog.action == "subscription.status_changed",
            )
        ).all()
        subscription_ids: set[uuid.UUID] = set()
        for audit_log in audit_logs:
            subscription_id = audit_log.metadata_json.get("subscription_id")
            if subscription_id is None:
                continue
            try:
                subscription_ids.add(uuid.UUID(str(subscription_id)))
            except ValueError:
                continue
        return subscription_ids

    def _merchant_key(self, transaction: Transaction) -> str:
        source = transaction.merchant_normalized or transaction.merchant_raw
        return normalize_merchant(source or "")

    def _display_merchant_name(self, merchant_key: str, transactions: list[Transaction]) -> str:
        raw_names = [transaction.merchant_raw.strip() for transaction in transactions if transaction.merchant_raw.strip()]
        if raw_names:
            return max(raw_names, key=raw_names.count)[:255]
        return merchant_key.title()[:255]

    def _average_amount(self, amounts: list[Decimal]) -> Decimal:
        total = sum(amounts, Decimal("0.00"))
        return (total / Decimal(len(amounts))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _amount_consistency(self, amounts: list[Decimal], average_amount: Decimal) -> float:
        if average_amount <= 0:
            return 0.0
        deviations = [abs(amount - average_amount) / average_amount for amount in amounts]
        mean_deviation = sum(deviations, Decimal("0")) / Decimal(len(deviations))
        return max(0.0, min(1.0, 1.0 - float(mean_deviation / Decimal("0.20"))))

    def _interval_consistency(self, *, frequency: str, intervals: list[int]) -> float:
        matching = [interval for interval in intervals if self._matches_frequency(frequency, interval)]
        if not matching:
            return 0.0
        match_score = len(matching) / len(intervals)
        if len(matching) == 1:
            spread_score = 1.0
        else:
            target = self.cadence_rules[frequency]["target"]
            spread = statistics.pstdev(matching)
            spread_score = max(0.0, min(1.0, 1.0 - (spread / max(float(target), 1.0))))
        return (match_score * 0.75) + (spread_score * 0.25)

    def _matches_frequency(self, frequency: str, interval: int) -> bool:
        rule = self.cadence_rules[frequency]
        if frequency == "monthly":
            return 26 <= interval <= 33
        return abs(interval - int(rule["target"])) <= int(rule["tolerance"])

    def _occurrence_score(self, *, frequency: str, count: int) -> float:
        if frequency == "yearly":
            return min(1.0, count / 2)
        return min(1.0, count / 4)

    def _category_score(self, transactions: list[Transaction]) -> float:
        if not transactions:
            return 0.0
        subscription_count = sum(
            1 for transaction in transactions if transaction.category == TransactionCategory.subscriptions.value
        )
        return subscription_count / len(transactions)

    def _known_subscription_score(self, merchant_key: str) -> float:
        if exact_merchant_categories.get(merchant_key) == TransactionCategory.subscriptions.value:
            return 1.0
        return 0.0

    def _confidence(
        self,
        *,
        occurrence_score: float,
        amount_consistency: float,
        interval_consistency: float,
        category_score: float,
        known_subscription_score: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                (occurrence_score * 0.25)
                + (interval_consistency * 0.30)
                + (amount_consistency * 0.25)
                + (category_score * 0.15)
                + (known_subscription_score * 0.05),
            ),
        )

    def _next_expected_date(self, *, last_seen: date, frequency: str, intervals: list[int]) -> date:
        if frequency == "weekly":
            return last_seen + timedelta(days=7)
        if frequency == "biweekly":
            return last_seen + timedelta(days=14)
        if frequency == "monthly":
            return self._add_months(last_seen, 1)
        if frequency == "yearly":
            return self._add_year(last_seen)
        median_interval = int(statistics.median(intervals))
        return last_seen + timedelta(days=median_interval)

    def _add_months(self, value: date, months: int) -> date:
        month_index = value.month - 1 + months
        year = value.year + (month_index // 12)
        month = (month_index % 12) + 1
        day = min(value.day, monthrange(year, month)[1])
        return date(year, month, day)

    def _add_year(self, value: date) -> date:
        try:
            return value.replace(year=value.year + 1)
        except ValueError:
            return date(value.year + 1, 2, 28)

    def _status(self, *, frequency: str, next_expected_date: date, as_of: date) -> str:
        days_after_expected = (as_of - next_expected_date).days
        if days_after_expected <= int(self.cadence_rules[frequency]["grace"]):
            return "active"
        if days_after_expected <= int(self.cadence_rules[frequency]["pause"]):
            return "paused"
        return "cancelled"
