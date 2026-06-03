from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_full_invoice_pipeline(client, test_db):
    """End-to-end: register → upload text invoice → verify extraction."""

    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "e2e@example.com",
            "password": "e2epassword",
            "full_name": "E2E User",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "e2e@example.com",
            "password": "e2epassword",
        },
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    invoice_text = b"""
    INVOICE
    Vendor: ACME Technologies Ltd
    GST: 29ABCDE1234F1Z5
    Invoice No: INV-2024-001
    Invoice Date: 2024-01-15
    Due Date: 2024-02-15

    Item                 Qty   Rate      Amount
    Cloud Services        1    10000     10000.00
    Support Services      1     5000      5000.00

    Subtotal:                            15000.00
    CGST (9%):                            1350.00
    SGST (9%):                            1350.00
    Total Amount:                        17700.00

    Payment Terms: Net 30
    """

    upload_resp = await client.post(
        "/api/v1/documents/upload",
        params={"doc_type": "invoice"},
        files={"file": ("test_invoice.txt", invoice_text, "text/plain")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]
    assert doc_id is not None

    doc_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert doc_resp.status_code == 200
