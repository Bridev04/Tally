from datetime import datetime
import uuid

from sqlmodel import SQLModel


class TransactionUploadCreate(SQLModel):
    user_id: uuid.UUID
    file_name: str
    upload_status: str = "pending"
    total_rows: int = 0
    processed_rows: int = 0
    error_message: str | None = None


class TransactionUploadUpdate(SQLModel):
    upload_status: str | None = None
    total_rows: int | None = None
    processed_rows: int | None = None
    error_message: str | None = None


class TransactionUploadRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    file_name: str
    upload_status: str
    total_rows: int
    processed_rows: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
