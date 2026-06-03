from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user
from backend.app.database import get_db
from backend.app.models.contract import Contract
from backend.app.models.invoice import Invoice
from backend.app.models.user import User
from backend.app.services.gemini_service import gemini_service

router = APIRouter()


@router.get("/vendors")
async def vendor_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(
        Invoice.vendor_name,
        func.count(Invoice.id).label("total_invoices"),
        func.sum(Invoice.total_amount).label("total_spend"),
        func.avg(Invoice.total_amount).label("avg_amount"),
        func.sum(Invoice.is_duplicate.cast(type_=None)).label("duplicate_count"),
    )
    if current_user.tenant_id:
        q = q.where(Invoice.tenant_id == current_user.tenant_id)
    q = q.group_by(Invoice.vendor_name).order_by(func.sum(Invoice.total_amount).desc()).limit(10)

    result = await db.execute(q)
    vendor_data = [
        {
            "vendor": r.vendor_name,
            "total_invoices": r.total_invoices,
            "total_spend": float(r.total_spend or 0),
            "avg_amount": float(r.avg_amount or 0),
            "duplicate_rate": (r.duplicate_count or 0) / max(r.total_invoices, 1),
        }
        for r in result.all()
    ]

    insights = await gemini_service.generate_insights({"vendor_performance": vendor_data})
    return {"vendors": vendor_data, "insights": insights}


@router.get("/cost-optimization")
async def cost_optimization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Invoice)
    if current_user.tenant_id:
        q = q.where(Invoice.tenant_id == current_user.tenant_id)
    invoices = (await db.execute(q)).scalars().all()

    total_duplicates = sum(1 for i in invoices if i.is_duplicate)
    duplicate_amount = sum(i.total_amount or 0 for i in invoices if i.is_duplicate)

    data = {
        "total_invoices": len(invoices),
        "duplicate_invoices": total_duplicates,
        "potential_savings_from_duplicates": duplicate_amount,
        "average_invoice_amount": sum(i.total_amount or 0 for i in invoices) / max(len(invoices), 1),
    }
    recommendations = await gemini_service.generate_insights(data)
    return {**data, "recommendations": recommendations}


@router.get("/contracts")
async def contract_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date, timedelta

    cutoff = date.today() + timedelta(days=60)
    q = select(Contract).where(Contract.expiration_date <= cutoff)
    if current_user.tenant_id:
        q = q.where(Contract.tenant_id == current_user.tenant_id)
    contracts = (await db.execute(q)).scalars().all()

    expiring = [
        {"id": c.id, "type": c.contract_type, "expiration": str(c.expiration_date), "risk_score": c.risk_score}
        for c in contracts
    ]
    insights = await gemini_service.generate_insights({"expiring_contracts": expiring})
    return {"expiring_contracts": expiring, "insights": insights}
