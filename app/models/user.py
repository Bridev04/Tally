import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.monthly_insight_report import MonthlyInsightReport
    from app.models.spending_anomaly import SpendingAnomaly
    from app.models.subscription import Subscription
    from app.models.transaction import Transaction
    from app.models.transaction_upload import TransactionUpload


class User(TimestampMixin, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(nullable=False, unique=True, index=True, max_length=320)
    password_hash: str = Field(nullable=False, max_length=255)

    uploads: list["TransactionUpload"] = Relationship(back_populates="user")
    transactions: list["Transaction"] = Relationship(back_populates="user")
    subscriptions: list["Subscription"] = Relationship(back_populates="user")
    spending_anomalies: list["SpendingAnomaly"] = Relationship(back_populates="user")
    monthly_insight_reports: list["MonthlyInsightReport"] = Relationship(back_populates="user")
    audit_logs: list["AuditLog"] = Relationship(back_populates="user")
