from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import SQLModel, Session, create_engine

from app.db.session import get_session
from app.main import app


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_check() -> None:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):  # noqa: ANN001
        del connection_record
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)

    def override_get_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    try:
        response = client.get("/health/db")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
