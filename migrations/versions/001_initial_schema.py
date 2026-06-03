"""Initial schema - all tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("gcs_path", sa.String(1000), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="uploaded"),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_name", sa.String(500), nullable=True),
        sa.Column("vendor_address", sa.Text(), nullable=True),
        sa.Column("vendor_email", sa.String(255), nullable=True),
        sa.Column("vendor_phone", sa.String(100), nullable=True),
        sa.Column("gst_number", sa.String(100), nullable=True),
        sa.Column("pan_number", sa.String(50), nullable=True),
        sa.Column("invoice_number", sa.String(200), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("purchase_order_number", sa.String(200), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=True),
        sa.Column("tax_amount", sa.Float(), nullable=True),
        sa.Column("discount_amount", sa.Float(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("payment_terms", sa.String(200), nullable=True),
        sa.Column("bank_account", sa.String(200), nullable=True),
        sa.Column("ifsc_code", sa.String(50), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=True),
        sa.Column("tax_breakdown", sa.JSON(), nullable=True),
        sa.Column("validation_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), default=False),
        sa.Column("duplicate_of", sa.String(36), sa.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("duplicate_score", sa.Float(), nullable=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_invoices_vendor_name", "invoices", ["vendor_name"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])
    op.create_index("ix_invoices_is_duplicate", "invoices", ["is_duplicate"])
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])

    op.create_table(
        "contracts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parties", sa.JSON(), nullable=True),
        sa.Column("contract_type", sa.String(200), nullable=True),
        sa.Column("contract_value", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("signed_date", sa.Date(), nullable=True),
        sa.Column("obligations", sa.JSON(), nullable=True),
        sa.Column("penalties", sa.JSON(), nullable=True),
        sa.Column("renewal_clauses", sa.JSON(), nullable=True),
        sa.Column("risk_clauses", sa.JSON(), nullable=True),
        sa.Column("termination_clauses", sa.JSON(), nullable=True),
        sa.Column("payment_terms", sa.JSON(), nullable=True),
        sa.Column("sla_terms", sa.JSON(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("risk_factors", sa.JSON(), nullable=True),
        sa.Column("compliance_flags", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("key_terms", sa.JSON(), nullable=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_contracts_tenant_id", "contracts", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("contracts")
    op.drop_table("invoices")
    op.drop_table("documents")
    op.drop_table("users")
    op.drop_table("tenants")
