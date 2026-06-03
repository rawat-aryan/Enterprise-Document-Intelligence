"""Unit tests for Gemini extraction service."""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.gemini_service import GeminiService, InvoiceExtraction, ContractExtraction


def test_parse_json_response_clean():
    svc = GeminiService()
    result = svc._parse_json_response('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_response_with_markdown():
    svc = GeminiService()
    result = svc._parse_json_response("```json\n{\"key\": \"value\"}\n```")
    assert result == {"key": "value"}


def test_parse_json_response_invalid():
    svc = GeminiService()
    result = svc._parse_json_response("not json at all")
    assert result == {}


def test_mock_invoice_extraction_finds_invoice_number():
    svc = GeminiService()
    text = "INVOICE NO: INV-2024-0001\nTotal Amount: Rs. 50,000"
    result = svc._mock_invoice_extraction(text)
    assert result.invoice_number is not None
    assert "INV-2024-0001" in result.invoice_number


def test_mock_invoice_extraction_finds_amount():
    svc = GeminiService()
    text = "Total Amount: 25000.00"
    result = svc._mock_invoice_extraction(text)
    assert result.total_amount == 25000.0


def test_mock_invoice_extraction_finds_gst():
    svc = GeminiService()
    text = "GST Number: 29ABCDE1234F1Z5\nTotal: 1000"
    result = svc._mock_invoice_extraction(text)
    assert result.gst_number == "29ABCDE1234F1Z5"


@pytest.mark.asyncio
async def test_extract_invoice_data_without_api_key():
    """Test that extraction falls back gracefully when API key is missing."""
    svc = GeminiService()
    svc._model = None  # Force mock path

    with patch.object(svc, "_get_model", return_value=None):
        result = await svc.extract_invoice_data("Invoice No: INV-001\nTotal: 5000")
    assert isinstance(result, InvoiceExtraction)


@pytest.mark.asyncio
async def test_extract_invoice_data_with_mock_gemini():
    """Test extraction with mocked Gemini response."""
    svc = GeminiService()

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "vendor_name": "Acme Corp",
        "invoice_number": "INV-001",
        "total_amount": 11800.0,
        "tax_amount": 1800.0,
        "subtotal": 10000.0,
        "currency": "INR",
        "confidence": 0.95,
    })

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch.object(svc, "_get_model", return_value=mock_model):
        result = await svc.extract_invoice_data("Some invoice text")

    assert result.vendor_name == "Acme Corp"
    assert result.invoice_number == "INV-001"
    assert result.total_amount == 11800.0
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_extract_contract_data_with_mock():
    svc = GeminiService()

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "parties": [{"name": "Company A", "role": "buyer"}, {"name": "Company B", "role": "seller"}],
        "contract_type": "Service Agreement",
        "effective_date": "2024-01-01",
        "expiration_date": "2024-12-31",
        "risk_score": 0.3,
        "risk_factors": ["auto-renewal clause"],
        "summary": "Annual service agreement",
    })

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch.object(svc, "_get_model", return_value=mock_model):
        result = await svc.extract_contract_data("Contract agreement text...")

    assert len(result.parties) == 2
    assert result.contract_type == "Service Agreement"
    assert result.risk_score == 0.3


@pytest.mark.asyncio
async def test_generate_sql_with_mock():
    svc = GeminiService()

    mock_response = MagicMock()
    mock_response.text = "SELECT vendor_name, SUM(total_amount) FROM invoices GROUP BY vendor_name"

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch.object(svc, "_get_model", return_value=mock_model):
        sql = await svc.generate_sql("Total spend by vendor", "invoices(vendor_name, total_amount)")

    assert "SELECT" in sql.upper()
    assert "vendor_name" in sql.lower()


@pytest.mark.asyncio
async def test_generate_insights_returns_string():
    svc = GeminiService()

    mock_response = MagicMock()
    mock_response.text = "• High spend detected\n• 3 vendors account for 80% of spend"

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch.object(svc, "_get_model", return_value=mock_model):
        result = await svc.generate_insights({"total_spend": 1000000, "vendor_count": 5})

    assert isinstance(result, str)
    assert len(result) > 0
