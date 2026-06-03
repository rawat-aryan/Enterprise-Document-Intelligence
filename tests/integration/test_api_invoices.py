from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document, DocumentType, DocumentStatus
from backend.app.models.invoice import Invoice, ValidationStatus


async def create_test_user_and_token(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": "invoice_user@example.com",
        "password": "password123",
        "full_name": "Invoice User",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "invoice_user@example.com",
        "password": "password123",
    })
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_list_invoices_empty(client: AsyncClient):
    token = await create_test_user_and_token(client)
    resp = await client.get("/api/v1/invoices/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_invoice_stats_empty(client: AsyncClient):
    token = await create_test_user_and_token(client)
    resp = await client.get("/api/v1/invoices/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_invoices"] == 0
    assert stats["total_amount"] == 0.0
