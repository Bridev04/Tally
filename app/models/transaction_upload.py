import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship

from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class TransactionUpload(TimestampMixin, table=True):
    __tablename__ = "transaction_uploads"
    __table_args__ = (
        CheckConstraint(
            "upload_status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_transaction_uploads_upload_status",
        ),
        CheckConstraint(
            "total_rows >= 0 AND processed_rows >= 0 AND processed_rows <= total_rows",
            name="ck_transaction_uploads_row_counts",
        ),
        CheckConstraint(
            "source IN ('csv', 'manual', 'paste', 'demo', 'ai_chat_manual')",
            name="ck_transaction_uploads_source",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    file_name: str = Field(nullable=False, max_length=255)
    upload_status: str = Field(default="pending", nullable=False, max_length=50)
    total_rows: int = Field(default=0, nullable=False)
    processed_rows: int = Field(default=0, nullable=False)
    error_message: str | None = Field(default=None, max_length=2000)
    source: str = Field(default="csv", nullable=False, index=True, max_length=20)
    is_demo: bool = Field(default=False, nullable=False, index=True)
    demo_scenario: str | None = Field(default=None, index=True, max_length=50)

    user: "User" = Relationship(back_populates="uploads")
    transactions: list["Transaction"] = Relationship(
        back_populates="upload",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
