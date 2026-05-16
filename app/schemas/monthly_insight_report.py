from datetime import date, datetime
from decimal import Decimal
import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


month_pattern = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class MonthlyReportGenerateRequest(BaseModel):
    month: str
    use_ai: bool = True
    force_refresh: bool = False

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        if month_pattern.fullmatch(value) is None:
            raise ValueError("month must use YYYY-MM format.")
        return value


class MonthlyReportFilterParams(BaseModel):
    month: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str | None) -> str | None:
        if value is not None and month_pattern.fullmatch(value) is None:
            raise ValueError("month must use YYYY-MM format.")
        return value


class TopCategoryReportItem(BaseModel):
    category: str
    total_amount: Decimal
    transaction_count: int
    percentage_of_total_expenses: Decimal


class SubscriptionReportItem(BaseModel):
    merchant_name: str
    average_amount: Decimal
    frequency: str
    next_expected_date: date | None
    confidence_score: float


class AnomalyReportItem(BaseModel):
    anomaly_type: str
    severity: str
    explanation: str
    amount_delta: Decimal | None
    percentage_change: float | None


class LargestMerchantReportItem(BaseModel):
    merchant_name: str
    total_amount: Decimal
    transaction_count: int


class MonthlyReportRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    month: str
    currency: str
    total_income: Decimal
    total_expenses: Decimal
    total_spend: Decimal
    net_flow: Decimal
    transaction_count: int
    top_categories: list[TopCategoryReportItem]
    detected_subscriptions: list[SubscriptionReportItem]
    anomalies: list[AnomalyReportItem]
    needs_review_count: int
    largest_merchant_total: LargestMerchantReportItem | None
    recurring_payment_count: int
    ai_summary: str
    generated_status: str
    generation_source: str
    safety_flags: list[str]
    has_data: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MonthlyReportListResponse(BaseModel):
    reports: list[MonthlyReportRead]
    limit: int
    offset: int
    count: int


class MonthlyReportSummaryData(BaseModel):
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
    has_data: bool


MonthlyInsightReportRead = MonthlyReportRead


class MonthlyInsightReportCreate(BaseModel):
    user_id: uuid.UUID
    month: date
    total_spend: Decimal
    top_categories_json: dict = Field(default_factory=dict)
    detected_subscriptions_json: list = Field(default_factory=list)
    anomalies_json: list = Field(default_factory=list)
    ai_summary: str | None = None


class MonthlyInsightReportUpdate(BaseModel):
    total_spend: Decimal | None = None
    top_categories_json: dict | None = None
    detected_subscriptions_json: list | None = None
    anomalies_json: list | None = None
    ai_summary: str | None = None
