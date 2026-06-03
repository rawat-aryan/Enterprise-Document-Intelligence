from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user
from backend.app.database import get_db
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.models.user import User
from backend.app.schemas.document import DocumentListResponse, DocumentResponse
from backend.app.services.extraction_service import extraction_service

router = APIRouter()

ALLOWED_TYPES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".txt", ".docx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Query(default="other"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {ext}")

    doc = Document(
        filename=file.filename,
        original_filename=file.filename,
        file_type=ext.lstrip("."),
        doc_type=doc_type,
        file_size=len(content),
        mime_type=file.content_type,
        status=DocumentStatus.UPLOADED.value,
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    background_tasks.add_task(extraction_service.process_document, doc.id, content, file.filename, db)

    return DocumentResponse.model_validate(doc)


@router.post("/bulk-upload", status_code=status.HTTP_202_ACCEPTED)
async def bulk_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Query(default="invoice"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=415, detail="Bulk upload requires a ZIP file")

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            file_names = [n for n in zf.namelist() if not n.endswith("/")]
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    created_ids = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for name in file_names:
            ext = "." + name.split(".")[-1].lower() if "." in name else ""
            if ext not in ALLOWED_TYPES:
                continue
            file_bytes = zf.read(name)
            doc = Document(
                filename=name,
                original_filename=name,
                file_type=ext.lstrip("."),
                doc_type=doc_type,
                file_size=len(file_bytes),
                status=DocumentStatus.UPLOADED.value,
                tenant_id=current_user.tenant_id,
                uploaded_by=current_user.id,
            )
            db.add(doc)
            await db.flush()
            created_ids.append(doc.id)
            background_tasks.add_task(extraction_service.process_document, doc.id, file_bytes, name, db)

    return {"message": f"Queued {len(created_ids)} documents for processing", "document_ids": created_ids}


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None),
    doc_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Document)
    if current_user.tenant_id:
        query = query.where(Document.tenant_id == current_user.tenant_id)
    if status_filter:
        query = query.where(Document.status == status_filter)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Document.created_at.desc())
    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.tenant_id and doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.tenant_id and doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(doc)
