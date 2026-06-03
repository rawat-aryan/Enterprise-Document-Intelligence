from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import TimestampMixin, UUIDMixin
from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant
    from backend.app.models.document import Document


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.ANALYST.value, nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="users")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="uploader", lazy="noload")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
