import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_campaigns_list():
    response = client.get("/api/v1/campaigns")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_copilot_chat():
    response = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze campaign ROAS and give recommendations"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data or "reply" in data
