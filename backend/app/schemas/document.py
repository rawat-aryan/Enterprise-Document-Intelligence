from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    filename: str
    file_type: str
    doc_type: str = "other"
    gcs_path: Optional[str] = None
    tenant_id: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    doc_type: str
    gcs_path: Optional[str] = None
    file_size: Optional[int] = None
    status: str
    confidence_score: Optional[float] = None
    extracted_data: Optional[dict[str, Any]] = None
    processing_error: Optional[str] = None
    tenant_id: Optional[str] = None
    uploaded_by: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentStatusUpdate(BaseModel):
    status: str
    processing_error: Optional[str] = None
    confidence_score: Optional[float] = None
