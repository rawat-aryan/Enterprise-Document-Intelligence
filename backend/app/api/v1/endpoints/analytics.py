from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.analytics import NLQueryRequest, NLQueryResponse
from backend.app.services.gemini_service import gemini_service

router = APIRouter()

SCHEMA_CONTEXT = """
Tables:
- invoices(id, vendor_name, invoice_number, invoice_date, due_date, total_amount, tax_amount, currency, validation_status, is_duplicate, tenant_id, created_at)
- documents(id, filename, doc_type, status, confidence_score, tenant_id, created_at)
- contracts(id, contract_type, effective_date, expiration_date, contract_value, risk_score, tenant_id, created_at)
"""


@router.post("/query", response_model=NLQueryResponse)
async def natural_language_query(
    payload: NLQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start = time.time()
    sql = await gemini_service.generate_sql(payload.question, SCHEMA_CONTEXT)

    # Safety: only allow SELECT
    if not sql.strip().upper().startswith("SELECT"):
        sql = "SELECT * FROM invoices LIMIT 10"

    try:
        result = await db.execute(text(sql))
        rows = [dict(zip(result.keys(), row)) for row in result.fetchmany(1000)]
    except Exception as e:
        rows = []
        sql = f"-- Query failed: {e}\n{sql}"

    insights = await gemini_service.generate_insights({"question": payload.question, "results": rows[:20]})
    elapsed = int((time.time() - start) * 1000)

    return NLQueryResponse(
        question=payload.question,
        sql=sql,
        results=rows,
        insights=insights,
        execution_time_ms=elapsed,
    )


@router.get("/spend")
async def get_spend_analytics(
    period: str = Query(default="month"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select, func
    from backend.app.models.invoice import Invoice

    q = select(
        Invoice.vendor_name,
        func.count(Invoice.id).label("invoice_count"),
        func.sum(Invoice.total_amount).label("total_spend"),
        func.avg(Invoice.total_amount).label("avg_amount"),
    )
    if current_user.tenant_id:
        q = q.where(Invoice.tenant_id == current_user.tenant_id)
    q = q.group_by(Invoice.vendor_name).order_by(func.sum(Invoice.total_amount).desc()).limit(20)

    result = await db.execute(q)
    vendors = [
        {"vendor": r.vendor_name, "invoice_count": r.invoice_count,
         "total_spend": float(r.total_spend or 0), "avg_amount": float(r.avg_amount or 0)}
        for r in result.all()
    ]
    return {"vendors": vendors, "period": period}
