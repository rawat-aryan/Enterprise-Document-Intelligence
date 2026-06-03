from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.services.duplicate_detection_service import (
    DuplicateDetectionService,
    _normalize_string,
    _string_similarity,
)


def test_normalize_string():
    assert _normalize_string("  ACME Corp  ") == "acmecorp"
    assert _normalize_string("INV-001/2024") == "inv0012024"
    assert _normalize_string(None) == ""


def test_string_similarity_identical():
    assert _string_similarity("acmecorp", "acmecorp") == 1.0


def test_string_similarity_different():
    sim = _string_similarity("acmecorp", "xyzcompany")
    assert 0.0 <= sim < 1.0


def test_string_similarity_empty():
    assert _string_similarity("", "something") == 0.0
    assert _string_similarity("something", "") == 0.0


@pytest.mark.asyncio
async def test_check_duplicate_no_existing():
    service = DuplicateDetectionService()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    )

    mock_invoice = MagicMock()
    mock_invoice.invoice_number = "INV-999"
    mock_invoice.vendor_name = "New Vendor"
    mock_invoice.total_amount = 5000.0
    mock_invoice.invoice_date = None
    mock_invoice.tenant_id = None

    result = await service.check_duplicate(mock_invoice, mock_db)
    assert result.is_duplicate is False
