from datetime import datetime
import uuid

from sqlmodel import Field, SQLModel


class AuditLogCreate(SQLModel):
    user_id: uuid.UUID
    action: str
    metadata_json: dict = Field(default_factory=dict)


class AuditLogRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action: str
    metadata_json: dict
    created_at: datetime
