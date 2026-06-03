from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.invoice import Invoice

logger = logging.getLogger(__name__)


def _normalize_string(s: Optional[str]) -> str:
    if not s:
        return ""
    return s.lower().strip().replace(" ", "").replace("-", "").replace("/", "")


def _string_similarity(a: str, b: str) -> float:
    """Compute simple character-based similarity."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    # Compute Jaccard similarity on character n-grams (bigrams)
    def bigrams(s):
        return set(s[i : i + 2] for i in range(len(s) - 1))

    ba, bb = bigrams(a), bigrams(b)
    if not ba and not bb:
        return 1.0
    if not ba or not bb:
        return 0.0
    intersection = len(ba & bb)
    union = len(ba | bb)
    return intersection / union


class DuplicateDetectionResult:
    def __init__(
        self,
        is_duplicate: bool,
        risk_score: float,
        duplicate_of: Optional[str] = None,
        reason: str = "",
    ):
        self.is_duplicate = is_duplicate
        self.risk_score = risk_score
        self.duplicate_of = duplicate_of
        self.reason = reason


class DuplicateDetectionService:
    EXACT_MATCH_THRESHOLD = 0.95
    FUZZY_MATCH_THRESHOLD = 0.80

    async def check_duplicate(
        self,
        invoice: Invoice,
        db: AsyncSession,
    ) -> DuplicateDetectionResult:
        """Check if an invoice is a duplicate of any existing invoice."""
        if not invoice.vendor_name and not invoice.invoice_number:
            return DuplicateDetectionResult(False, 0.0, reason="Insufficient data")

        # Fetch candidate invoices from same tenant (or all if no tenant)
        query = select(Invoice).where(Invoice.id != invoice.id)
        if invoice.tenant_id:
            query = query.where(Invoice.tenant_id == invoice.tenant_id)
        if invoice.vendor_name:
            # Pre-filter by similar vendor names using DB
            pass

        result = await db.execute(query.limit(1000))
        candidates = result.scalars().all()

        best_score = 0.0
        best_match_id = None
        best_reason = ""

        for candidate in candidates:
            score, reason = self._compute_similarity(invoice, candidate)
            if score > best_score:
                best_score = score
                best_match_id = candidate.id
                best_reason = reason

        is_duplicate = best_score >= self.EXACT_MATCH_THRESHOLD
        return DuplicateDetectionResult(
            is_duplicate=is_duplicate,
            risk_score=best_score,
            duplicate_of=best_match_id if is_duplicate else None,
            reason=best_reason,
        )

    def _compute_similarity(self, a: Invoice, b: Invoice) -> tuple[float, str]:
        """Compute similarity score between two invoices. Returns (score, reason)."""
        scores = []
        reasons = []

        # Exact invoice number match is a strong signal
        norm_inv_a = _normalize_string(a.invoice_number)
        norm_inv_b = _normalize_string(b.invoice_number)
        if norm_inv_a and norm_inv_b:
            inv_sim = _string_similarity(norm_inv_a, norm_inv_b)
            scores.append(("invoice_number", inv_sim, 0.40))
            if inv_sim >= 0.95:
                reasons.append(f"Invoice number match: {a.invoice_number}")

        # Vendor name similarity
        norm_vendor_a = _normalize_string(a.vendor_name)
        norm_vendor_b = _normalize_string(b.vendor_name)
        if norm_vendor_a and norm_vendor_b:
            vendor_sim = _string_similarity(norm_vendor_a, norm_vendor_b)
            scores.append(("vendor", vendor_sim, 0.25))
            if vendor_sim >= 0.90:
                reasons.append(f"Vendor match: {a.vendor_name}")

        # Amount similarity (within 1%)
        if a.total_amount and b.total_amount and a.total_amount > 0:
            amount_diff_pct = abs(a.total_amount - b.total_amount) / a.total_amount
            amount_sim = max(0.0, 1.0 - amount_diff_pct * 10)
            scores.append(("amount", amount_sim, 0.20))
            if amount_sim >= 0.99:
                reasons.append(f"Amount match: {a.total_amount}")

        # Date proximity (within 7 days = high similarity)
        if a.invoice_date and b.invoice_date:
            days_diff = abs((a.invoice_date - b.invoice_date).days)
            date_sim = max(0.0, 1.0 - days_diff / 30)
            scores.append(("date", date_sim, 0.15))

        # GST number exact match
        if a.gst_number and b.gst_number:
            gst_sim = 1.0 if a.gst_number.strip() == b.gst_number.strip() else 0.0
            scores.append(("gst", gst_sim, 0.10))
            if gst_sim == 1.0:
                reasons.append(f"GST match: {a.gst_number}")

        if not scores:
            return 0.0, "No comparable fields"

        # Weighted average
        total_weight = sum(w for _, _, w in scores)
        weighted_sum = sum(s * w for _, s, w in scores)
        final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        reason = "; ".join(reasons) if reasons else "Low similarity"
        return final_score, reason

    def compute_batch_duplicates(self, invoices: list[Invoice]) -> list[tuple[int, int, float]]:
        """Find duplicates within a batch. Returns list of (idx_a, idx_b, score)."""
        duplicates = []
        for i in range(len(invoices)):
            for j in range(i + 1, len(invoices)):
                score, _ = self._compute_similarity(invoices[i], invoices[j])
                if score >= self.FUZZY_MATCH_THRESHOLD:
                    duplicates.append((i, j, score))
        return duplicates


duplicate_detection_service = DuplicateDetectionService()
