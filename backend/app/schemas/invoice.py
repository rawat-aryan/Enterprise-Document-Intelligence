from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    tax_rate: Optional[float] = None
    hsn_code: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: str
    document_id: str
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_email: Optional[str] = None
    gst_number: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total_amount: Optional[float] = None
    currency: str = "INR"
    payment_terms: Optional[str] = None
    line_items: Optional[list[dict[str, Any]]] = None
    validation_status: str
    validation_errors: Optional[list[str]] = None
    confidence_score: Optional[float] = None
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    duplicate_score: Optional[float] = None
    tenant_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int


class InvoiceStats(BaseModel):
    total_invoices: int
    total_amount: float
    average_amount: float
    duplicate_count: int
    validation_breakdown: dict[str, int]
    currency_breakdown: dict[str, float]
    monthly_totals: list[dict[str, Any]]
