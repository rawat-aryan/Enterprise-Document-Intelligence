from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.document import Document
    from backend.app.models.user import User


class Tenant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", lazy="selectin")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug}>"
