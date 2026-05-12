from datetime import datetime
from decimal import Decimal
import uuid

from sqlmodel import SQLModel


class SpendingAnomalyCreate(SQLModel):
    user_id: uuid.UUID
    anomaly_type: str
    category: str | None = None
    merchant_name: str | None = None
    amount_delta: Decimal | None = None
    percentage_change: float | None = None
    explanation: str
    severity: str = "medium"


class SpendingAnomalyRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    anomaly_type: str
    category: str | None
    merchant_name: str | None
    amount_delta: Decimal | None
    percentage_change: float | None
    explanation: str
    severity: str
    created_at: datetime
