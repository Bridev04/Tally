from collections.abc import Generator
import os

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-enough-length")

from app.api.routes import auth as auth_routes  # noqa: E402
from app.api.routes import imports as import_routes  # noqa: E402
from app.api.routes import subscriptions as subscription_routes  # noqa: E402
from app.api.routes import transactions as transaction_routes  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def engine():
    database_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(database_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):  # noqa: ANN001
        del connection_record
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(database_engine)
    return database_engine


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:  # noqa: ANN001
    with Session(engine) as test_session:
        yield test_session


@pytest.fixture()
def client(session: Session):  # noqa: ANN201
    def override_get_session() -> Generator[Session, None, None]:
        yield session

    auth_routes.auth_rate_limiter = None
    import_routes.import_rate_limiter = None
    subscription_routes.subscription_rate_limiter = None
    transaction_routes.transaction_rate_limiter = None
    app.dependency_overrides[get_session] = override_get_session
    yield app
    app.dependency_overrides.clear()
    auth_routes.auth_rate_limiter = None
    import_routes.import_rate_limiter = None
    subscription_routes.subscription_rate_limiter = None
    transaction_routes.transaction_rate_limiter = None
