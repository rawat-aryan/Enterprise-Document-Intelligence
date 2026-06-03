from __future__ import annotations

from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.document import Document


class ValidationStatus(str, Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"


class Invoice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "invoices"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Vendor info
    vendor_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    vendor_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vendor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vendor_phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    pan_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Invoice details
    invoice_number: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    purchase_order_number: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Amounts
    subtotal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tax_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    total_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    # Payment
    payment_terms: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_account: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Line items and metadata
    line_items: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    tax_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Validation & processing
    validation_status: Mapped[str] = mapped_column(
        String(50), default=ValidationStatus.PENDING.value, nullable=False, index=True
    )
    validation_errors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Duplicate detection
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    duplicate_of: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Multi-tenancy
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="invoice")
    duplicate_invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice", remote_side="Invoice.id", foreign_keys=[duplicate_of]
    )

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} number={self.invoice_number} vendor={self.vendor_name}>"
