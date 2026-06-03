from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    reg_resp = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepassword",
        "full_name": "New User",
        "role": "analyst",
    })
    assert reg_resp.status_code == 201
    user = reg_resp.json()
    assert user["email"] == "newuser@example.com"

    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "newuser@example.com",
        "password": "securepassword",
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


@pytest.mark.asyncio
async def test_upload_document_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/documents/upload")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "doc_user@example.com",
        "password": "password123",
        "full_name": "Doc User",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "doc_user@example.com",
        "password": "password123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/documents/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
