from __future__ import annotations

from calendar import monthrange
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import logging
import re
import uuid

from sqlmodel import Session, select

from app.core.config import Settings
from app.models import MonthlyInsightReport, SpendingAnomaly, Subscription, Transaction, User
from app.models.common import utc_now
from app.schemas.monthly_insight_report import (
    AnomalyReportItem,
    LargestMerchantReportItem,
    MonthlyReportRead,
    MonthlyReportSummaryData,
    SubscriptionReportItem,
    TopCategoryReportItem,
)
from app.services.audit import create_audit_log
from app.services.llm.base import MonthlySummaryLLM
from app.services.llm.client import build_monthly_summary_llm
from app.services.llm.schemas import MonthlySummaryInput
from app.services.transaction_import_utils import normalize_merchant


logger = logging.getLogger(__name__)

month_pattern = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
expense_excluded_categories = {"income", "transfer"}
forbidden_summary_patterns = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\byou should\b",
        r"\byou must\b",
        r"\bcancel\b",
        r"\bstop spending\b",
        r"\bbad spending\b",
        r"\bwaste(?:ful)?\b",
        r"\binvest(?:ment|ing)?\b",
        r"\bloan\b",
        r"\bcredit card\b",
        r"(?<!not )\bfinancial advice\b",
        r"\bguaranteed\b",
        r"\bprofit\b",
    ]
]


def validate_month_label(month: str) -> None:
    if month_pattern.fullmatch(month) is None:
        raise ValueError("month must use YYYY-MM format.")


def is_safe_monthly_summary(summary: str) -> bool:
    lowered = summary.lower()
    return not any(pattern.search(lowered) for pattern in forbidden_summary_patterns)


class MonthlyReportService:
    low_confidence_threshold = 0.72

    def generate(
        self,
        *,
        session: Session,
        current_user: User,
        month: str,
        settings: Settings,
        use_ai: bool = True,
        force_refresh: bool = False,
        llm_client: MonthlySummaryLLM | None = None,
    ) -> MonthlyInsightReport:
        validate_month_label(month)
        month_start, month_end = self._month_window(month)
        existing = self._get_existing(session=session, user_id=current_user.id, month_start=month_start)
        if existing is not None and not force_refresh:
            return existing

        summary_data = self._build_summary_data(
            session=session,
            user_id=current_user.id,
            month=month,
            month_start=month_start,
            month_end=month_end,
            low_confidence_threshold=settings.dashboard_low_confidence_threshold,
        )
        fallback_summary = self.deterministic_summary(summary_data)
        generation_source = "deterministic"
        generated_status = "complete"
        safety_flags: list[str] = []
        final_summary = fallback_summary

        if use_ai:
            llm = llm_client if llm_client is not None else build_monthly_summary_llm(settings)
            if llm is None:
                generation_source = "llm_fallback"
                generated_status = "fallback"
                safety_flags.append("llm_unavailable")
            else:
                try:
                    ai_summary = llm.generate_monthly_summary(
                        MonthlySummaryInput(**summary_data.model_dump())
                    ).strip()
                except RuntimeError:
                    generation_source = "llm_fallback"
                    generated_status = "fallback"
                    safety_flags.append("llm_unavailable")
                else:
                    if ai_summary and is_safe_monthly_summary(ai_summary):
                        final_summary = ai_summary[:4000]
                        generation_source = "llm"
                    else:
                        generation_source = "llm_fallback"
                        generated_status = "fallback"
                        safety_flags.append("unsafe_ai_summary_rejected")
                        logger.info(
                            "Monthly report AI summary failed safety validation",
                            extra={
                                "user_id": str(current_user.id),
                                "month": month,
                                "generation_source": generation_source,
                                "safety_validation_status": "rejected",
                            },
                        )

        report = existing or MonthlyInsightReport(user_id=current_user.id, month=month_start)
        report.total_spend = summary_data.total_expenses
        report.total_income = summary_data.total_income
        report.net_flow = summary_data.net_flow
        report.transaction_count = summary_data.transaction_count
        report.top_categories_json = {
            "items": [item.model_dump(mode="json") for item in summary_data.top_categories],
            "currency": summary_data.currency,
            "needs_review_count": summary_data.needs_review_count,
            "largest_merchant_total": (
                summary_data.largest_merchant_total.model_dump(mode="json")
                if summary_data.largest_merchant_total is not None
                else None
            ),
            "has_data": summary_data.has_data,
        }
        report.detected_subscriptions_json = [
            item.model_dump(mode="json") for item in summary_data.detected_subscriptions
        ]
        report.anomalies_json = [item.model_dump(mode="json") for item in summary_data.anomalies]
        report.ai_summary = final_summary
        report.generated_status = generated_status
        report.generation_source = generation_source
        report.safety_flags_json = safety_flags
        report.updated_at = utc_now()
        session.add(report)
        session.flush()
        session.refresh(report)

        create_audit_log(
            session=session,
            user_id=current_user.id,
            action="monthly_report.generated",
            metadata={
                "month": month,
                "generation_source": generation_source,
                "safety_validation_status": "passed" if not safety_flags else "fallback",
            },
        )
        logger.info(
            "Monthly report generated",
            extra={
                "user_id": str(current_user.id),
                "month": month,
                "generation_source": generation_source,
                "safety_validation_status": "passed" if not safety_flags else "fallback",
            },
        )
        return report

    def list_reports(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month: str | None,
        limit: int,
        offset: int,
    ) -> list[MonthlyInsightReport]:
        statement = select(MonthlyInsightReport).where(MonthlyInsightReport.user_id == user_id)
        if month is not None:
            validate_month_label(month)
            statement = statement.where(MonthlyInsightReport.month == self._month_window(month)[0])
        return session.exec(
            statement.order_by(MonthlyInsightReport.month.desc(), MonthlyInsightReport.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()

    def get_for_user(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> MonthlyInsightReport | None:
        report = session.get(MonthlyInsightReport, report_id)
        if report is None or report.user_id != user_id:
            return None
        return report

    def to_read(self, report: MonthlyInsightReport) -> MonthlyReportRead:
        top_category_payload = report.top_categories_json or {}
        top_categories = top_category_payload.get("items", [])
        largest = top_category_payload.get("largest_merchant_total")
        return MonthlyReportRead(
            id=report.id,
            user_id=report.user_id,
            month=report.month.strftime("%Y-%m"),
            currency=top_category_payload.get("currency") or "PHP",
            total_income=report.total_income,
            total_expenses=report.total_spend,
            total_spend=report.total_spend,
            net_flow=report.net_flow,
            transaction_count=report.transaction_count,
            top_categories=[TopCategoryReportItem(**item) for item in top_categories],
            detected_subscriptions=[SubscriptionReportItem(**item) for item in report.detected_subscriptions_json],
            anomalies=[AnomalyReportItem(**item) for item in report.anomalies_json],
            needs_review_count=int(top_category_payload.get("needs_review_count") or 0),
            largest_merchant_total=LargestMerchantReportItem(**largest) if largest else None,
            recurring_payment_count=len(report.detected_subscriptions_json),
            ai_summary=report.ai_summary or self.deterministic_summary_from_report(report),
            generated_status=report.generated_status,
            generation_source=report.generation_source,
            safety_flags=list(report.safety_flags_json or []),
            has_data=bool(top_category_payload.get("has_data", report.transaction_count > 0)),
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    def deterministic_summary_from_report(self, report: MonthlyInsightReport) -> str:
        return (
            f"Based on imported transactions for {report.month.strftime('%B %Y')}, total expenses were "
            f"{self._format_money(report.total_spend)} across {report.transaction_count} transactions. "
            "This is a neutral summary of imported data, not financial advice."
        )

    def deterministic_summary(self, summary_data: MonthlyReportSummaryData) -> str:
        month_name = self._month_name(summary_data.month)
        if not summary_data.has_data:
            return (
                f"Based on imported transactions for {month_name}, no transactions were found for this month. "
                "This is a neutral summary of imported data, not financial advice."
            )

        categories = [item.category.replace("_", " ") for item in summary_data.top_categories[:3]]
        category_text = ", ".join(categories) if categories else "no expense categories"
        return (
            f"Based on imported transactions for {month_name}, total expenses were "
            f"{summary_data.currency} {summary_data.total_expenses:,.2f} across "
            f"{summary_data.transaction_count} transactions. The largest categories were {category_text}. "
            f"Tally also detected {summary_data.recurring_payment_count} active recurring payments and "
            f"{len(summary_data.anomalies)} spending patterns that may be worth reviewing. "
            "This is a neutral summary of imported data, not financial advice."
        )

    def _build_summary_data(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month: str,
        month_start: date,
        month_end: date,
        low_confidence_threshold: float,
    ) -> MonthlyReportSummaryData:
        transactions = session.exec(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date <= month_end,
            )
            .order_by(Transaction.transaction_date.asc(), Transaction.created_at.asc())
        ).all()
        total_income = self._money(sum((item.amount for item in transactions if item.amount > 0), Decimal("0")))
        total_expenses = self._money(sum((-item.amount for item in transactions if item.amount < 0), Decimal("0")))
        currency = self._currency_for(transactions)
        return MonthlyReportSummaryData(
            month=month,
            currency=currency,
            total_income=total_income,
            total_expenses=total_expenses,
            net_flow=self._money(total_income - total_expenses),
            transaction_count=len(transactions),
            top_categories=self._top_categories(transactions=transactions, total_expenses=total_expenses),
            detected_subscriptions=self._subscriptions(session=session, user_id=user_id),
            anomalies=self._anomalies(
                session=session,
                user_id=user_id,
                month_start=month_start,
                month_end=month_end,
            ),
            needs_review_count=self._needs_review_count(
                transactions=transactions,
                low_confidence_threshold=low_confidence_threshold,
            ),
            largest_merchant_total=self._largest_merchant_total(transactions),
            recurring_payment_count=self._active_subscription_count(session=session, user_id=user_id),
            has_data=bool(transactions),
        )

    def _get_existing(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month_start: date,
    ) -> MonthlyInsightReport | None:
        return session.exec(
            select(MonthlyInsightReport)
            .where(MonthlyInsightReport.user_id == user_id, MonthlyInsightReport.month == month_start)
            .order_by(MonthlyInsightReport.created_at.desc())
            .limit(1)
        ).first()

    def _top_categories(
        self,
        *,
        transactions: list[Transaction],
        total_expenses: Decimal,
    ) -> list[TopCategoryReportItem]:
        totals: dict[str, tuple[Decimal, int]] = {}
        for transaction in transactions:
            category = transaction.category or "needs_review"
            if transaction.amount >= 0 or category in expense_excluded_categories:
                continue
            current_total, current_count = totals.get(category, (Decimal("0"), 0))
            totals[category] = (current_total + (-transaction.amount), current_count + 1)

        return [
            TopCategoryReportItem(
                category=category,
                total_amount=self._money(amount),
                transaction_count=count,
                percentage_of_total_expenses=self._percentage(amount, total_expenses),
            )
            for category, (amount, count) in sorted(totals.items(), key=lambda item: (-item[1][0], item[0]))[:5]
        ]

    def _subscriptions(self, *, session: Session, user_id: uuid.UUID) -> list[SubscriptionReportItem]:
        subscriptions = session.exec(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status == "active")
            .order_by(Subscription.next_expected_date.asc(), Subscription.merchant_name.asc())
            .limit(20)
        ).all()
        return [
            SubscriptionReportItem(
                merchant_name=item.merchant_name,
                average_amount=item.average_amount,
                frequency=item.frequency,
                next_expected_date=item.next_expected_date,
                confidence_score=item.confidence_score,
            )
            for item in subscriptions
        ]

    def _active_subscription_count(self, *, session: Session, user_id: uuid.UUID) -> int:
        return len(
            session.exec(select(Subscription).where(Subscription.user_id == user_id, Subscription.status == "active")).all()
        )

    def _anomalies(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        month_start: date,
        month_end: date,
    ) -> list[AnomalyReportItem]:
        anomalies = session.exec(select(SpendingAnomaly).where(SpendingAnomaly.user_id == user_id)).all()
        matching = [item for item in anomalies if self._anomaly_in_month(item, month_start=month_start, month_end=month_end)]
        matching = sorted(matching, key=lambda item: (self._severity_rank(item.severity), item.created_at), reverse=False)[:5]
        return [
            AnomalyReportItem(
                anomaly_type=item.anomaly_type,
                severity=item.severity,
                explanation=item.explanation,
                amount_delta=item.amount_delta,
                percentage_change=item.percentage_change,
            )
            for item in matching
        ]

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

    def _largest_merchant_total(self, transactions: list[Transaction]) -> LargestMerchantReportItem | None:
        totals: dict[str, tuple[str, Decimal, int]] = {}
        for transaction in transactions:
            category = transaction.category or "needs_review"
            if transaction.amount >= 0 or category in expense_excluded_categories:
                continue
            merchant_key = normalize_merchant(transaction.merchant_normalized or transaction.merchant_raw or "")
            if not merchant_key:
                continue
            display = transaction.merchant_raw.strip() or merchant_key.title()
            _, current_total, current_count = totals.get(merchant_key, (display, Decimal("0"), 0))
            totals[merchant_key] = (display, current_total + (-transaction.amount), current_count + 1)
        if not totals:
            return None
        merchant_name, total, count = max(totals.values(), key=lambda item: (item[1], item[0]))
        return LargestMerchantReportItem(
            merchant_name=merchant_name,
            total_amount=self._money(total),
            transaction_count=count,
        )

    def _currency_for(self, transactions: list[Transaction]) -> str:
        currencies = [item.currency for item in transactions if item.currency]
        if not currencies:
            return "PHP"
        return Counter(currencies).most_common(1)[0][0]

    def _anomaly_in_month(self, anomaly: SpendingAnomaly, *, month_start: date, month_end: date) -> bool:
        if anomaly.period_start is None and anomaly.period_end is None:
            return False
        period_start = anomaly.period_start or anomaly.period_end
        period_end = anomaly.period_end or anomaly.period_start
        return bool(period_start and period_end and period_start <= month_end and period_end >= month_start)

    def _month_window(self, month: str) -> tuple[date, date]:
        validate_month_label(month)
        year, month_number = (int(part) for part in month.split("-", 1))
        return date(year, month_number, 1), date(year, month_number, monthrange(year, month_number)[1])

    def _month_name(self, month: str) -> str:
        year, month_number = (int(part) for part in month.split("-", 1))
        return date(year, month_number, 1).strftime("%B %Y")

    def _money(self, value: Decimal | int | float) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _percentage(self, value: Decimal, total: Decimal) -> Decimal:
        if total == 0:
            return Decimal("0.00")
        return ((value / total) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _format_money(self, value: Decimal) -> str:
        return f"PHP {value:,.2f}"

    def _severity_rank(self, severity: str) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)
