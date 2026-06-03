from __future__ import annotations

import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user
from backend.app.database import get_db
from backend.app.models.invoice import Invoice
from backend.app.models.user import User
from backend.app.services.excel_service import excel_service

router = APIRouter()


@router.get("/excel")
async def generate_excel_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Invoice)
    if current_user.tenant_id:
        query = query.where(Invoice.tenant_id == current_user.tenant_id)
    result = await db.execute(query)
    invoices = result.scalars().all()

    invoice_dicts = [
        {
            "vendor_name": i.vendor_name,
            "invoice_number": i.invoice_number,
            "invoice_date": str(i.invoice_date) if i.invoice_date else None,
            "total_amount": i.total_amount,
            "tax_amount": i.tax_amount,
            "currency": i.currency,
            "validation_status": i.validation_status,
            "is_duplicate": i.is_duplicate,
            "duplicate_score": i.duplicate_score,
            "confidence_score": i.confidence_score,
            "validation_errors": i.validation_errors or [],
        }
        for i in invoices
    ]

    workbook_bytes = excel_service.generate_invoice_report(invoice_dicts)

    return StreamingResponse(
        io.BytesIO(workbook_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=invoice_report.xlsx"},
    )
