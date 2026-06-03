"""Integration tests for analytics API endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


async def _get_auth_token(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": "analytics_user@example.com",
        "password": "password123",
        "full_name": "Analytics User",
        "role": "analyst",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "analytics_user@example.com",
        "password": "password123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_nl_query_endpoint(client: AsyncClient):
    token = await _get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "backend.app.services.gemini_service.gemini_service.generate_sql",
        new_callable=AsyncMock,
        return_value="SELECT * FROM invoices LIMIT 5",
    ), patch(
        "backend.app.services.gemini_service.gemini_service.generate_insights",
        new_callable=AsyncMock,
        return_value="No invoices found yet.",
    ):
        resp = await client.post(
            "/api/v1/analytics/query",
            json={"question": "Show me all invoices"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "sql" in data
    assert "results" in data
    assert "question" in data
    assert data["question"] == "Show me all invoices"


@pytest.mark.asyncio
async def test_spend_analytics_endpoint(client: AsyncClient):
    token = await _get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/analytics/spend", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "vendors" in data
    assert isinstance(data["vendors"], list)


@pytest.mark.asyncio
async def test_nl_query_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/analytics/query",
        json={"question": "Show all invoices"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_nl_query_blocks_non_select(client: AsyncClient):
    """Ensure only SELECT queries are allowed."""
    token = await _get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "backend.app.services.gemini_service.gemini_service.generate_sql",
        new_callable=AsyncMock,
        return_value="DROP TABLE invoices",
    ), patch(
        "backend.app.services.gemini_service.gemini_service.generate_insights",
        new_callable=AsyncMock,
        return_value="N/A",
    ):
        resp = await client.post(
            "/api/v1/analytics/query",
            json={"question": "Delete all data"},
            headers=headers,
        )

    assert resp.status_code == 200
    # Should have fallen back to safe SELECT
    data = resp.json()
    assert data["sql"].upper().startswith("SELECT")
