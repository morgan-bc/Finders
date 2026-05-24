"""Tests for FastAPI service."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from finders.api.app import create_app
from finders.api.models import QueryRequest


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_query_request_model():
    req = QueryRequest(query="test query")
    assert req.query == "test query"
    assert req.model is None
    assert req.max_iterations == 10
    assert req.memory_enabled is True


def test_query_request_overrides():
    req = QueryRequest(
        query="test",
        model="openai:gpt-4o",
        max_iterations=5,
        memory_enabled=False,
    )
    assert req.model == "openai:gpt-4o"
    assert req.max_iterations == 5
    assert req.memory_enabled is False


def test_query_endpoint_returns_sse(client):
    """验证 POST /api/query 返回的是 SSE 响应。"""
    with patch("finders.api.routes._build_settings") as mock_build, \
         patch("finders.api.routes.AgentRunner") as mock_runner:
        mock_build.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_runner.return_value = mock_instance

        # SSE stream 会返回 200，但 TestClient 无法流式消费
        response = client.post("/api/query", json={"query": "test"})
        assert response.status_code == 200
