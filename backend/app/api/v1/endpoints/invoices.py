from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user
from backend.app.database import get_db
from backend.app.models.invoice import Invoice, ValidationStatus
from backend.app.models.user import User
from backend.app.schemas.invoice import InvoiceListResponse, InvoiceResponse, InvoiceStats

router = APIRouter()


@router.get("/", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    vendor: Optional[str] = Query(default=None),
    validation_status: Optional[str] = Query(default=None),
    duplicates_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Invoice)
    if current_user.tenant_id:
        query = query.where(Invoice.tenant_id == current_user.tenant_id)
    if vendor:
        query = query.where(Invoice.vendor_name.ilike(f"%{vendor}%"))
    if validation_status:
        query = query.where(Invoice.validation_status == validation_status)
    if duplicates_only:
        query = query.where(Invoice.is_duplicate.is_(True))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Invoice.created_at.desc())
    invoices = (await db.execute(query)).scalars().all()

    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=InvoiceStats)
async def get_invoice_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = select(Invoice)
    if current_user.tenant_id:
        base = base.where(Invoice.tenant_id == current_user.tenant_id)

    invoices = (await db.execute(base)).scalars().all()

    total_amount = sum(i.total_amount or 0.0 for i in invoices)
    duplicate_count = sum(1 for i in invoices if i.is_duplicate)
    validation_breakdown = {}
    for status in ValidationStatus:
        validation_breakdown[status.value] = sum(1 for i in invoices if i.validation_status == status.value)

    currency_breakdown: dict = {}
    for inv in invoices:
        if inv.total_amount:
            currency_breakdown[inv.currency] = currency_breakdown.get(inv.currency, 0.0) + inv.total_amount

    from collections import defaultdict

    monthly: dict = defaultdict(float)
    for inv in invoices:
        if inv.invoice_date:
            key = inv.invoice_date.strftime("%Y-%m")
            monthly[key] += inv.total_amount or 0.0
    monthly_totals = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    return InvoiceStats(
        total_invoices=len(invoices),
        total_amount=total_amount,
        average_amount=total_amount / len(invoices) if invoices else 0.0,
        duplicate_count=duplicate_count,
        validation_breakdown=validation_breakdown,
        currency_breakdown=currency_breakdown,
        monthly_totals=monthly_totals,
    )


@router.get("/duplicates", response_model=InvoiceListResponse)
async def get_duplicates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Invoice).where(Invoice.is_duplicate.is_(True))
    if current_user.tenant_id:
        query = query.where(Invoice.tenant_id == current_user.tenant_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.offset((page - 1) * page_size).limit(page_size)
    invoices = (await db.execute(query)).scalars().all()

    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if current_user.tenant_id and invoice.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return InvoiceResponse.model_validate(invoice)
