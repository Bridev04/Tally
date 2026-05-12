from datetime import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, JSON
from sqlmodel import Field, Relationship, SQLModel

from app.models.common import utc_now

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    action: str = Field(nullable=False, max_length=255)
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    user: "User" = Relationship(back_populates="audit_logs")
