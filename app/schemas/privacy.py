from datetime import date, datetime
from decimal import Decimal
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.transaction import StrictSchema


DELETE_APP_DATA_CONFIRMATION = "DELETE MY TALLY DATA"
DELETE_ACCOUNT_CONFIRMATION = "DELETE MY ACCOUNT"


class DataSourcesUsed(BaseModel):
    csv_upload: bool
    manual_entry: bool
    paste_import: bool
    demo_data: bool


class PrivacySummaryResponse(BaseModel):
    user_email: str
    transaction_count: int
    upload_count: int
    subscription_count: int
    anomaly_count: int
    monthly_report_count: int
    has_demo_data: bool
    latest_upload_date: datetime | None
    latest_report_date: datetime | None
    data_sources_used: DataSourcesUsed
    privacy_notes: list[str]


class ExportMetadata(BaseModel):
    exported_at: datetime
    app: Literal["Tally"]
    scope: Literal["current_user"]
    notice: str


class ExportUser(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime


class ExportUpload(BaseModel):
    id: uuid.UUID
    file_name: str
    upload_status: str
    total_rows: int
    processed_rows: int
    created_at: datetime
    updated_at: datetime


class ExportTransaction(BaseModel):
    id: uuid.UUID
    upload_id: uuid.UUID
    transaction_date: date
    merchant_raw: str
    merchant_normalized: str | None
    description: str | None
    amount: Decimal
    currency: str
    category: str | None
    category_confidence: float | None
    category_manually_set: bool
    category_source: str
    categorization_reason: str | None
    categorization_rule: str | None
    payment_type: str | None
    is_recurring_candidate: bool
    created_at: datetime
    updated_at: datetime


class ExportSubscription(BaseModel):
    id: uuid.UUID
    merchant_name: str
    average_amount: Decimal
    frequency: str
    first_seen: date
    last_seen: date
    next_expected_date: date | None
    confidence_score: float
    status: str
    created_at: datetime
    updated_at: datetime


class ExportAnomaly(BaseModel):
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


class ExportMonthlyReport(BaseModel):
    id: uuid.UUID
    month: date
    total_spend: Decimal
    total_income: Decimal
    net_flow: Decimal
    transaction_count: int
    top_categories_json: dict
    detected_subscriptions_json: list
    anomalies_json: list
    ai_summary: str | None
    generated_status: str
    generation_source: str
    safety_flags_json: list
    created_at: datetime
    updated_at: datetime


class DataExportResponse(BaseModel):
    metadata: ExportMetadata
    user: ExportUser
    uploads: list[ExportUpload]
    transactions: list[ExportTransaction]
    subscriptions: list[ExportSubscription]
    anomalies: list[ExportAnomaly]
    monthly_reports: list[ExportMonthlyReport]


class DeletedCounts(BaseModel):
    transactions: int = 0
    uploads: int = 0
    subscriptions: int = 0
    anomalies: int = 0
    monthly_reports: int = 0
    audit_logs: int = 0
    user: int = 0


class ClearDemoDataResponse(BaseModel):
    message: str
    deleted_counts: DeletedCounts


class DeleteAppDataRequest(StrictSchema):
    confirmation: str = Field(min_length=len(DELETE_APP_DATA_CONFIRMATION), max_length=len(DELETE_APP_DATA_CONFIRMATION))

    @field_validator("confirmation")
    @classmethod
    def validate_confirmation(cls, value: str) -> str:
        if value != DELETE_APP_DATA_CONFIRMATION:
            raise ValueError("Confirmation text does not match.")
        return value


class DeleteAppDataResponse(BaseModel):
    message: str
    deleted_counts: DeletedCounts


class DeleteAccountRequest(StrictSchema):
    confirmation: str = Field(min_length=len(DELETE_ACCOUNT_CONFIRMATION), max_length=len(DELETE_ACCOUNT_CONFIRMATION))

    @field_validator("confirmation")
    @classmethod
    def validate_confirmation(cls, value: str) -> str:
        if value != DELETE_ACCOUNT_CONFIRMATION:
            raise ValueError("Confirmation text does not match.")
        return value


class DeleteAccountResponse(BaseModel):
    message: str
    deleted_counts: DeletedCounts
    session_notice: str
