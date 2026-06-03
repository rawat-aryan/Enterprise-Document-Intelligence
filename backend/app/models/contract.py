from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import TimestampMixin, UUIDMixin
from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.document import Document


class Contract(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "contracts"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Parties
    parties: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    contract_type: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contract_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    # Dates
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    signed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Clauses
    obligations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    penalties: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    renewal_clauses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    risk_clauses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    termination_clauses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    payment_terms: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    sla_terms: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Risk scoring
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_factors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    compliance_flags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Summary
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_terms: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Multi-tenancy
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="contract")

    def __repr__(self) -> str:
        return f"<Contract id={self.id} type={self.contract_type} risk={self.risk_score}>"
