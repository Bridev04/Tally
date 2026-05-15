from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.transaction import StrictSchema


month_pattern = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class AnomalyType(StrEnum):
    category_spike = "CATEGORY_SPIKE"
    merchant_frequency_spike = "MERCHANT_FREQUENCY_SPIKE"
    repeated_small_purchases = "REPEATED_SMALL_PURCHASES"
    subscription_price_change = "SUBSCRIPTION_PRICE_CHANGE"
    duplicate_like_transactions = "DUPLICATE_LIKE_TRANSACTIONS"
    needs_review_cluster = "NEEDS_REVIEW_CLUSTER"


class Severity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class SpendingAnomalyCreate(BaseModel):
    user_id: uuid.UUID
    anomaly_type: str
    category: str | None = None
    merchant_name: str | None = None
    amount_delta: Decimal | None = None
    percentage_change: float | None = None
    explanation: str
    severity: str = Severity.medium.value
    period_start: date | None = None
    period_end: date | None = None
    baseline_period_start: date | None = None
    baseline_period_end: date | None = None
    transaction_count: int | None = None
    metadata_json: dict = Field(default_factory=dict)


class AnomalyDetectRequest(StrictSchema):
    month: str | None = None
    force_refresh: bool = False

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str | None) -> str | None:
        if value is not None and month_pattern.fullmatch(value) is None:
            raise ValueError("month must use YYYY-MM format.")
        return value


class SpendingAnomalyRead(BaseModel):
    id: uuid.UUID
    anomaly_type: str
    category: str | None
    merchant_name: str | None
    amount_delta: Decimal | None
    percentage_change: float | None
    explanation: str
    severity: str
    period_start: date | None
    period_end: date | None
    baseline_period_start: date | None
    baseline_period_end: date | None
    transaction_count: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalyListResponse(BaseModel):
    anomalies: list[SpendingAnomalyRead]
    limit: int
    offset: int
    count: int


class AnomalyDetectionResponse(BaseModel):
    anomalies: list[SpendingAnomalyRead]
    detected_count: int
    month: str


class AnomalyFilterParams(BaseModel):
    month: str | None = None
    severity: Severity | None = None
    anomaly_type: AnomalyType | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str | None) -> str | None:
        if value is not None and month_pattern.fullmatch(value) is None:
            raise ValueError("month must use YYYY-MM format.")
        return value


class AnomalySummaryItem(BaseModel):
    name: str
    count: int


class AnomalySummaryResponse(BaseModel):
    total_anomalies: int
    high_count: int
    medium_count: int
    low_count: int
    top_categories: list[AnomalySummaryItem]
    top_merchants: list[AnomalySummaryItem]
    month: str
