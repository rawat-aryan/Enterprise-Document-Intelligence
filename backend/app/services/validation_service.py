from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

from backend.app.models.invoice import Invoice, ValidationStatus

VALID_GST_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$")
VALID_PAN_PATTERN = re.compile(r"^[A-Z]{5}\d{4}[A-Z]{1}$")


class ValidationReport:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.is_valid: bool = True

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)


class ValidationService:
    def validate_invoice(self, invoice: Invoice) -> ValidationReport:
        report = ValidationReport()

        # Required field checks
        if not invoice.vendor_name or not invoice.vendor_name.strip():
            report.add_error("Vendor name is missing")
        if not invoice.invoice_number:
            report.add_error("Invoice number is missing")
        if invoice.total_amount is None:
            report.add_error("Total amount is missing")

        # Amount validations
        if invoice.total_amount is not None:
            if invoice.total_amount <= 0:
                report.add_error(f"Total amount must be positive, got {invoice.total_amount}")
            if invoice.total_amount > 10_000_000:
                report.add_warning(f"Unusually large amount: {invoice.total_amount}")

        # Tax calculation check
        if invoice.subtotal is not None and invoice.tax_amount is not None and invoice.total_amount is not None:
            expected = invoice.subtotal + invoice.tax_amount - (invoice.discount_amount or 0)
            if abs(expected - invoice.total_amount) > 1.0:
                report.add_warning(
                    f"Amount mismatch: subtotal({invoice.subtotal}) + tax({invoice.tax_amount}) "
                    f"- discount({invoice.discount_amount or 0}) = {expected:.2f} "
                    f"but total is {invoice.total_amount:.2f}"
                )

        # Date validations
        if invoice.invoice_date is not None:
            today = date.today()
            if invoice.invoice_date > today:
                report.add_error(f"Invoice date {invoice.invoice_date} is in the future")
            if (today - invoice.invoice_date).days > 365 * 5:
                report.add_warning(f"Invoice date {invoice.invoice_date} is more than 5 years ago")

        if invoice.due_date is not None and invoice.invoice_date is not None:
            if invoice.due_date < invoice.invoice_date:
                report.add_error("Due date cannot be before invoice date")

        # GST number format
        if invoice.gst_number:
            if not VALID_GST_PATTERN.match(invoice.gst_number.strip().upper()):
                report.add_warning(f"GST number format appears invalid: {invoice.gst_number}")

        # PAN number format
        if invoice.pan_number:
            if not VALID_PAN_PATTERN.match(invoice.pan_number.strip().upper()):
                report.add_warning(f"PAN number format appears invalid: {invoice.pan_number}")

        # Line items check
        if invoice.line_items:
            line_total = sum(item.get("amount", 0) or 0 for item in invoice.line_items if isinstance(item, dict))
            if invoice.subtotal is not None and line_total > 0:
                if abs(line_total - invoice.subtotal) > 1.0:
                    report.add_warning(
                        f"Line items total ({line_total:.2f}) does not match subtotal ({invoice.subtotal:.2f})"
                    )

        return report

    def apply_validation(self, invoice: Invoice, report: ValidationReport) -> Invoice:
        invoice.validation_errors = report.errors + [f"WARNING: {w}" for w in report.warnings]
        if report.is_valid and not report.warnings:
            invoice.validation_status = ValidationStatus.VALID.value
        elif not report.is_valid:
            invoice.validation_status = ValidationStatus.INVALID.value
        else:
            invoice.validation_status = ValidationStatus.NEEDS_REVIEW.value
        return invoice

    def validate_date_field(self, date_val: Any) -> Optional[date]:
        if date_val is None:
            return None
        if isinstance(date_val, date):
            return date_val
        if isinstance(date_val, str):
            formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]
            for fmt in formats:
                try:
                    return datetime.strptime(date_val.strip(), fmt).date()
                except ValueError:
                    continue
        return None


validation_service = ValidationService()
