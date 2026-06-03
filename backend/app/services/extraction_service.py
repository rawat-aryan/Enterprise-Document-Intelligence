from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.contract import Contract
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.models.invoice import Invoice
from backend.app.services.duplicate_detection_service import duplicate_detection_service
from backend.app.services.gemini_service import gemini_service
from backend.app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)


def _safe_date(date_str: Optional[str]):
    if not date_str:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


class ExtractionService:
    async def process_document(
        self,
        document_id: str,
        file_bytes: bytes,
        filename: str,
        db: AsyncSession,
    ) -> None:
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found")
            return

        try:
            doc.status = DocumentStatus.PROCESSING.value
            await db.commit()

            # OCR
            ocr_result = await ocr_service.extract_text_from_file(file_bytes, filename)
            doc.raw_text = ocr_result.text

            # Determine type and extract
            if doc.doc_type == DocumentType.INVOICE.value:
                await self._extract_invoice(doc, ocr_result.text, db)
            elif doc.doc_type == DocumentType.CONTRACT.value:
                await self._extract_contract(doc, ocr_result.text, db)
            else:
                # Auto-detect
                text_lower = ocr_result.text.lower()
                if any(k in text_lower for k in ["invoice", "bill to", "gst", "total amount"]):
                    doc.doc_type = DocumentType.INVOICE.value
                    await self._extract_invoice(doc, ocr_result.text, db)
                elif any(k in text_lower for k in ["agreement", "contract", "parties", "whereas"]):
                    doc.doc_type = DocumentType.CONTRACT.value
                    await self._extract_contract(doc, ocr_result.text, db)

            doc.status = DocumentStatus.VALIDATED.value
            doc.confidence_score = ocr_result.confidence
            doc.processed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            logger.error(f"Processing failed for {document_id}: {e}")
            doc.status = DocumentStatus.FAILED.value
            doc.processing_error = str(e)
            await db.commit()

    async def _extract_invoice(self, doc: Document, text: str, db: AsyncSession) -> None:
        extraction = await gemini_service.extract_invoice_data(text)
        validation = await gemini_service.validate_extraction(extraction.model_dump())

        invoice = Invoice(
            document_id=doc.id,
            vendor_name=extraction.vendor_name,
            vendor_address=extraction.vendor_address,
            vendor_email=extraction.vendor_email,
            vendor_phone=extraction.vendor_phone,
            gst_number=extraction.gst_number,
            pan_number=extraction.pan_number,
            invoice_number=extraction.invoice_number,
            invoice_date=_safe_date(extraction.invoice_date),
            due_date=_safe_date(extraction.due_date),
            purchase_order_number=extraction.purchase_order_number,
            subtotal=extraction.subtotal,
            tax_amount=extraction.tax_amount,
            discount_amount=extraction.discount_amount,
            total_amount=extraction.total_amount,
            currency=extraction.currency,
            payment_terms=extraction.payment_terms,
            bank_account=extraction.bank_account,
            ifsc_code=extraction.ifsc_code,
            line_items=[li.model_dump() for li in extraction.line_items],
            tax_breakdown=extraction.tax_breakdown,
            validation_status="valid" if validation.is_valid else "needs_review",
            validation_errors=validation.errors,
            confidence_score=extraction.confidence,
            tenant_id=doc.tenant_id,
        )
        db.add(invoice)
        await db.flush()

        # Duplicate detection
        dup_result = await duplicate_detection_service.check_duplicate(invoice, db)
        if dup_result.is_duplicate:
            invoice.is_duplicate = True
            invoice.duplicate_of = dup_result.duplicate_of
            invoice.duplicate_score = dup_result.risk_score

        doc.extracted_data = extraction.model_dump()

    async def _extract_contract(self, doc: Document, text: str, db: AsyncSession) -> None:
        extraction = await gemini_service.extract_contract_data(text)

        contract = Contract(
            document_id=doc.id,
            parties=extraction.parties,
            contract_type=extraction.contract_type,
            contract_value=extraction.contract_value,
            currency=extraction.currency,
            effective_date=_safe_date(extraction.effective_date),
            expiration_date=_safe_date(extraction.expiration_date),
            signed_date=_safe_date(extraction.signed_date),
            obligations=extraction.obligations,
            penalties=extraction.penalties,
            renewal_clauses=extraction.renewal_clauses,
            risk_clauses=extraction.risk_clauses,
            termination_clauses=extraction.termination_clauses,
            payment_terms=extraction.payment_terms,
            sla_terms=extraction.sla_terms,
            risk_score=extraction.risk_score,
            risk_factors=extraction.risk_factors,
            summary=extraction.summary,
            key_terms=extraction.key_terms,
            tenant_id=doc.tenant_id,
        )
        db.add(contract)
        doc.extracted_data = extraction.model_dump()


extraction_service = ExtractionService()
