from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():

    response = client.get(
        "/api/v1/health"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "document-intelligence"


def test_documents_endpoint():

    response = client.get(
        "/api/v1/documents"
    )

    assert response.status_code == 200

    data = response.json()

    assert "documents" in data
    assert isinstance(data["documents"], list)


def test_swagger_endpoint():

    response = client.get("/docs")

    assert response.status_code == 200