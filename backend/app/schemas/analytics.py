from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class NLQueryRequest(BaseModel):
    question: str
    tenant_id: Optional[str] = None


class NLQueryResponse(BaseModel):
    question: str
    sql: str
    results: list[dict[str, Any]]
    chart_data: Optional[dict[str, Any]] = None
    insights: Optional[str] = None
    execution_time_ms: int


class SpendAnalytics(BaseModel):
    total_spend: float
    currency: str
    period: str
    by_vendor: list[dict[str, Any]]
    by_month: list[dict[str, Any]]
    by_category: list[dict[str, Any]]
    top_vendors: list[dict[str, Any]]


class VendorAnalytics(BaseModel):
    vendor_name: str
    total_invoices: int
    total_amount: float
    average_amount: float
    duplicate_rate: float
    on_time_payment_rate: float
    risk_score: float


class TrendAnalytics(BaseModel):
    period: str
    data_points: list[dict[str, Any]]
    trend_direction: str
    growth_rate: float
    anomalies: list[dict[str, Any]]
