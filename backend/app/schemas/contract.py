from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel


class ContractResponse(BaseModel):
    id: str
    document_id: str
    parties: Optional[list[dict[str, Any]]] = None
    contract_type: Optional[str] = None
    contract_value: Optional[float] = None
    currency: str = "INR"
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    signed_date: Optional[date] = None
    obligations: Optional[list[str]] = None
    penalties: Optional[list[dict[str, Any]]] = None
    renewal_clauses: Optional[list[str]] = None
    risk_clauses: Optional[list[str]] = None
    risk_score: Optional[float] = None
    risk_factors: Optional[list[str]] = None
    summary: Optional[str] = None
    tenant_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int
    page: int
    page_size: int
