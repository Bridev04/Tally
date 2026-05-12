from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin(SQLModel):
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
        sa_column_kwargs={"onupdate": utc_now},
    )
