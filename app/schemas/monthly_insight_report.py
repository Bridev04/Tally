from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlmodel import Field, SQLModel


class MonthlyInsightReportCreate(SQLModel):
    user_id: uuid.UUID
    month: date
    total_spend: Decimal
    top_categories_json: dict = Field(default_factory=dict)
    detected_subscriptions_json: list = Field(default_factory=list)
    anomalies_json: list = Field(default_factory=list)
    ai_summary: str | None = None


class MonthlyInsightReportUpdate(SQLModel):
    total_spend: Decimal | None = None
    top_categories_json: dict | None = None
    detected_subscriptions_json: list | None = None
    anomalies_json: list | None = None
    ai_summary: str | None = None


class MonthlyInsightReportRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    month: date
    total_spend: Decimal
    top_categories_json: dict
    detected_subscriptions_json: list
    anomalies_json: list
    ai_summary: str | None
    created_at: datetime
