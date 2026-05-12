from fastapi.testclient import TestClient


def test_health_check(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_check(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    response = test_client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
