"""Unit tests for AI extraction service (Claude/Gemini/regex backends)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.ai_service import (
    AIService,
    ContractExtraction,
    InvoiceExtraction,
    _parse_json,
    _regex_invoice,
)

# ── _parse_json helper ────────────────────────────────────────────────────────


def test_parse_json_clean():
    assert _parse_json('{"key": "value"}') == {"key": "value"}


def test_parse_json_with_markdown():
    assert _parse_json('```json\n{"key": "value"}\n```') == {"key": "value"}


def test_parse_json_invalid():
    assert _parse_json("not json at all") == {}


def test_parse_json_embedded():
    assert _parse_json('some text {"key": 1} more text') == {"key": 1}


# ── _regex_invoice fallback ───────────────────────────────────────────────────


def test_regex_finds_invoice_number():
    result = _regex_invoice("INVOICE NO: INV-2024-0001\nTotal Amount: Rs. 50,000")
    assert result.invoice_number is not None
    assert "INV-2024-0001" in result.invoice_number


def test_regex_finds_amount():
    result = _regex_invoice("Total Amount: 25000.00")
    assert result.total_amount == 25000.0


def test_regex_finds_gst():
    result = _regex_invoice("GST Number: 29ABCDE1234F1Z5\nTotal: 1000")
    assert result.gst_number == "29ABCDE1234F1Z5"


def test_regex_confidence_is_low():
    result = _regex_invoice("Invoice No: X\nTotal: 100")
    assert result.confidence == 0.4


# ── AIService — no API key (regex fallback) ───────────────────────────────────


@pytest.mark.asyncio
async def test_extract_invoice_no_api_key():
    svc = AIService()
    svc._backend = None  # force regex path
    result = await svc.extract_invoice_data("Invoice No: INV-001\nTotal: 5000")
    assert isinstance(result, InvoiceExtraction)


@pytest.mark.asyncio
async def test_extract_contract_no_api_key():
    svc = AIService()
    svc._backend = None
    result = await svc.extract_contract_data("This is a contract.")
    assert isinstance(result, ContractExtraction)


@pytest.mark.asyncio
async def test_generate_sql_no_api_key():
    svc = AIService()
    svc._backend = None
    sql = await svc.generate_sql("spend by vendor", "invoices(vendor_name, total_amount)")
    assert "SELECT" in sql.upper()


@pytest.mark.asyncio
async def test_generate_insights_no_api_key():
    svc = AIService()
    svc._backend = None
    result = await svc.generate_insights({"total": 100})
    assert isinstance(result, str)


# ── AIService — Claude backend (mocked) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_invoice_claude_mock():
    svc = AIService()
    mock_backend = MagicMock()
    mock_backend.extract_invoice.return_value = InvoiceExtraction(
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        total_amount=11800.0,
        tax_amount=1800.0,
        subtotal=10000.0,
        currency="INR",
        confidence=0.95,
    )
    svc._backend = mock_backend
    result = await svc.extract_invoice_data("Some invoice text")
    assert result.vendor_name == "Acme Corp"
    assert result.invoice_number == "INV-001"
    assert result.total_amount == 11800.0
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_extract_contract_claude_mock():
    svc = AIService()
    mock_backend = MagicMock()
    mock_backend.extract_contract.return_value = ContractExtraction(
        parties=[{"name": "Company A", "role": "buyer"}, {"name": "Company B", "role": "seller"}],
        contract_type="Service Agreement",
        effective_date="2024-01-01",
        expiration_date="2024-12-31",
        risk_score=0.3,
        risk_factors=["auto-renewal clause"],
        summary="Annual service agreement",
    )
    svc._backend = mock_backend
    result = await svc.extract_contract_data("Contract agreement text...")
    assert len(result.parties) == 2
    assert result.contract_type == "Service Agreement"
    assert result.risk_score == 0.3


@pytest.mark.asyncio
async def test_generate_sql_claude_mock():
    svc = AIService()
    mock_backend = MagicMock()
    mock_backend.generate_sql.return_value = "SELECT vendor_name, SUM(total_amount) FROM invoices GROUP BY vendor_name"
    svc._backend = mock_backend
    sql = await svc.generate_sql("Total spend by vendor", "invoices(vendor_name, total_amount)")
    assert "SELECT" in sql.upper()
    assert "vendor_name" in sql.lower()


@pytest.mark.asyncio
async def test_generate_insights_claude_mock():
    svc = AIService()
    mock_backend = MagicMock()
    mock_backend.generate_insights.return_value = "• High spend\n• 3 vendors = 80% of spend"
    svc._backend = mock_backend
    result = await svc.generate_insights({"total_spend": 1_000_000, "vendor_count": 5})
    assert isinstance(result, str)
    assert len(result) > 0
