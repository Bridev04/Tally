from fastapi.testclient import TestClient


def test_health_check(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "database" not in response.json()
    assert "database_url" not in response.text.lower()
    assert "jwt" not in response.text.lower()


def test_health_check_allows_configured_local_expo_origin(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)

    response = test_client.get("/health", headers={"origin": "http://localhost:8081"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8081"


def test_database_health_check(client) -> None:  # noqa: ANN001
    test_client = TestClient(client)
    response = test_client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
