from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user
from backend.app.database import get_db
from backend.app.models.contract import Contract
from backend.app.models.user import User
from backend.app.schemas.contract import ContractListResponse, ContractResponse

router = APIRouter()


@router.get("/", response_model=ContractListResponse)
async def list_contracts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    expiring_days: Optional[int] = Query(default=None, description="Filter contracts expiring within N days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date, timedelta

    query = select(Contract)
    if current_user.tenant_id:
        query = query.where(Contract.tenant_id == current_user.tenant_id)
    if expiring_days is not None:
        cutoff = date.today() + timedelta(days=expiring_days)
        query = query.where(Contract.expiration_date <= cutoff)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Contract.created_at.desc())
    contracts = (await db.execute(query)).scalars().all()

    return ContractListResponse(
        items=[ContractResponse.model_validate(c) for c in contracts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.tenant_id and contract.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ContractResponse.model_validate(contract)
