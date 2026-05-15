from datetime import date, datetime
from decimal import Decimal
import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


month_pattern = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class DashboardFilterParams(BaseModel):
    month: str | None = None

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str | None) -> str | None:
        if value is not None and month_pattern.fullmatch(value) is None:
            raise ValueError("month must use YYYY-MM format.")
        return value


class TopCategoryItem(BaseModel):
    category: str
    total_amount: Decimal
    transaction_count: int
    percentage_of_total_expenses: Decimal


class RecentTransactionItem(BaseModel):
    id: uuid.UUID
    transaction_date: date
    merchant_normalized: str | None
    description: str | None
    amount: Decimal
    currency: str
    category: str | None
    category_confidence: float | None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionDashboardItem(BaseModel):
    id: uuid.UUID
    merchant_name: str
    average_amount: Decimal
    frequency: str
    next_expected_date: date | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class SubscriptionDashboardSummary(BaseModel):
    active_count: int
    estimated_monthly_total: Decimal
    upcoming_items: list[SubscriptionDashboardItem]


class AnomalyDashboardItem(BaseModel):
    id: uuid.UUID
    anomaly_type: str
    category: str | None
    merchant_name: str | None
    amount_delta: Decimal | None
    percentage_change: float | None
    explanation: str
    severity: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalyDashboardSummary(BaseModel):
    total_count: int
    high_count: int
    medium_count: int
    low_count: int
    latest_items: list[AnomalyDashboardItem]


class LatestUploadSummary(BaseModel):
    id: uuid.UUID
    file_name: str
    upload_status: str
    total_rows: int
    processed_rows: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    month: str | None
    currency: str
    total_income: Decimal
    total_expenses: Decimal
    net_flow: Decimal
    transaction_count: int
    top_categories: list[TopCategoryItem]
    recent_transactions: list[RecentTransactionItem]
    subscription_summary: SubscriptionDashboardSummary
    anomaly_summary: AnomalyDashboardSummary
    needs_review_count: int
    latest_upload: LatestUploadSummary | None
    has_data: bool

