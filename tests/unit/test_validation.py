"""Unit tests for validation service."""
from __future__ import annotations

from datetime import date
import pytest
from backend.app.services.validation_service import ValidationService
from backend.app.models.invoice import Invoice, ValidationStatus


def _make_invoice(**kwargs):
    """Create a simple namespace object that behaves like an Invoice for validation."""
    from types import SimpleNamespace
    defaults = {
        "id": "test-id",
        "document_id": "doc-id",
        "vendor_name": "Test Vendor",
        "invoice_number": "INV-001",
        "total_amount": 11800.0,
        "subtotal": 10000.0,
        "tax_amount": 1800.0,
        "discount_amount": 0.0,
        "currency": "INR",
        "validation_status": ValidationStatus.PENDING.value,
        "is_duplicate": False,
        "invoice_date": None,
        "due_date": None,
        "gst_number": None,
        "pan_number": None,
        "line_items": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_validate_valid_invoice():
    service = ValidationService()
    invoice = _make_invoice(
        invoice_date=date(2024, 1, 15),
        due_date=date(2024, 2, 15),
    )
    report = service.validate_invoice(invoice)
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_validate_missing_vendor_name():
    service = ValidationService()
    invoice = _make_invoice(vendor_name=None)
    report = service.validate_invoice(invoice)
    assert not report.is_valid
    assert any("vendor" in e.lower() for e in report.errors)


def test_validate_missing_invoice_number():
    service = ValidationService()
    invoice = _make_invoice(invoice_number=None)
    report = service.validate_invoice(invoice)
    assert not report.is_valid
    assert any("invoice number" in e.lower() for e in report.errors)


def test_validate_negative_amount():
    service = ValidationService()
    invoice = _make_invoice(total_amount=-1000.0)
    report = service.validate_invoice(invoice)
    assert not report.is_valid
    assert any("positive" in e.lower() for e in report.errors)


def test_validate_tax_mismatch():
    service = ValidationService()
    # subtotal + tax != total (100 off)
    invoice = _make_invoice(subtotal=10000.0, tax_amount=1800.0, total_amount=12000.0)
    report = service.validate_invoice(invoice)
    # Should produce a warning about amount mismatch
    assert len(report.warnings) > 0


def test_validate_future_invoice_date():
    service = ValidationService()
    invoice = _make_invoice(invoice_date=date(2099, 1, 1))
    report = service.validate_invoice(invoice)
    assert not report.is_valid
    assert any("future" in e.lower() for e in report.errors)


def test_validate_due_date_before_invoice_date():
    service = ValidationService()
    invoice = _make_invoice(
        invoice_date=date(2024, 6, 1),
        due_date=date(2024, 5, 1),
    )
    report = service.validate_invoice(invoice)
    assert not report.is_valid
    assert any("due date" in e.lower() for e in report.errors)


def test_validate_invalid_gst_format():
    service = ValidationService()
    invoice = _make_invoice(gst_number="INVALID_GST_12345")
    report = service.validate_invoice(invoice)
    assert any("gst" in w.lower() for w in report.warnings)


def test_apply_validation_valid():
    service = ValidationService()
    invoice = _make_invoice()
    report = service.validate_invoice(invoice)
    updated = service.apply_validation(invoice, report)
    assert updated.validation_status in (
        ValidationStatus.VALID.value,
        ValidationStatus.NEEDS_REVIEW.value,
    )
