import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class TransactionUpload(TimestampMixin, table=True):
    __tablename__ = "transaction_uploads"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    file_name: str = Field(nullable=False, max_length=255)
    upload_status: str = Field(default="pending", nullable=False, max_length=50)
    total_rows: int = Field(default=0, nullable=False)
    processed_rows: int = Field(default=0, nullable=False)
    error_message: str | None = Field(default=None, max_length=2000)

    user: "User" = Relationship(back_populates="uploads")
    transactions: list["Transaction"] = Relationship(back_populates="upload")
