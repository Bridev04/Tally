from datetime import datetime
import uuid

from pydantic import EmailStr
from sqlmodel import SQLModel


class UserCreate(SQLModel):
    email: EmailStr
    password_hash: str


class UserUpdate(SQLModel):
    email: EmailStr | None = None
    password_hash: str | None = None


class UserRead(SQLModel):
    id: uuid.UUID
    email: EmailStr
    created_at: datetime
    updated_at: datetime
