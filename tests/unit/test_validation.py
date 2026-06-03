from __future__ import annotations

import pytest
from backend.app.services.validation_service import InvoiceValidator


def test_validate_valid_invoice():
    validator = InvoiceValidator()
    data = {
        "vendor_name": "ACME Corp",
        "invoice_number": "INV-001",
        "invoice_date": "2024-01-15",
        "total_amount": 11800.0,
        "tax_amount": 1800.0,
        "subtotal": 10000.0,
        "currency": "INR",
    }
    result = validator.validate(data)
    assert result.confidence > 0.5


def test_validate_missing_required_fields():
    validator = InvoiceValidator()
    data = {"currency": "INR"}
    result = validator.validate(data)
    assert len(result.errors) > 0


def test_validate_tax_mismatch():
    validator = InvoiceValidator()
    data = {
        "vendor_name": "Test Vendor",
        "invoice_number": "INV-002",
        "total_amount": 10000.0,
        "tax_amount": 5000.0,   # 50% tax - suspicious
        "subtotal": 5000.0,
        "currency": "INR",
    }
    result = validator.validate(data)
    assert any("tax" in w.lower() for w in result.warnings)


def test_validate_negative_amount():
    validator = InvoiceValidator()
    data = {
        "vendor_name": "Bad Vendor",
        "invoice_number": "INV-003",
        "total_amount": -1000.0,
        "currency": "INR",
    }
    result = validator.validate(data)
    assert len(result.errors) > 0


def test_validate_gst_format():
    validator = InvoiceValidator()
    data = {
        "vendor_name": "GST Vendor",
        "invoice_number": "INV-004",
        "total_amount": 1000.0,
        "gst_number": "INVALID_GST",
        "currency": "INR",
    }
    result = validator.validate(data)
    assert any("gst" in w.lower() for w in result.warnings)
