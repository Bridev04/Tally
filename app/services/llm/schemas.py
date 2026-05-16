from decimal import Decimal

from pydantic import BaseModel

from app.schemas.monthly_insight_report import (
    AnomalyReportItem,
    LargestMerchantReportItem,
    SubscriptionReportItem,
    TopCategoryReportItem,
)


class MonthlySummaryInput(BaseModel):
    month: str
    currency: str
    total_income: Decimal
    total_expenses: Decimal
    net_flow: Decimal
    transaction_count: int
    top_categories: list[TopCategoryReportItem]
    detected_subscriptions: list[SubscriptionReportItem]
    anomalies: list[AnomalyReportItem]
    needs_review_count: int
    largest_merchant_total: LargestMerchantReportItem | None
    recurring_payment_count: int
