"""
AI service — uses Claude (Anthropic) when CLAUDE_API_KEY is set,
falls back to Gemini when GEMINI_API_KEY is set,
falls back to regex-based extraction when neither is available.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.app.config import settings

logger = logging.getLogger(__name__)


# ── Pydantic extraction models (shared by both backends) ─────────────────────


class LineItemExtraction(BaseModel):
    description: str = ""
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    tax_rate: Optional[float] = None
    hsn_code: Optional[str] = None


class InvoiceExtraction(BaseModel):
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_phone: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    purchase_order_number: Optional[str] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total_amount: Optional[float] = None
    currency: str = "INR"
    payment_terms: Optional[str] = None
    bank_account: Optional[str] = None
    ifsc_code: Optional[str] = None
    line_items: list[LineItemExtraction] = []
    tax_breakdown: dict[str, Any] = {}
    confidence: float = 0.0


class ContractExtraction(BaseModel):
    parties: list[dict[str, Any]] = []
    contract_type: Optional[str] = None
    contract_value: Optional[float] = None
    currency: str = "INR"
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    signed_date: Optional[str] = None
    obligations: list[str] = []
    penalties: list[dict[str, Any]] = []
    renewal_clauses: list[str] = []
    risk_clauses: list[str] = []
    termination_clauses: list[str] = []
    payment_terms: dict[str, Any] = {}
    sla_terms: dict[str, Any] = {}
    risk_score: float = 0.0
    risk_factors: list[str] = []
    summary: Optional[str] = None
    key_terms: dict[str, Any] = {}


class ReportExtraction(BaseModel):
    title: Optional[str] = None
    report_date: Optional[str] = None
    period: Optional[str] = None
    author: Optional[str] = None
    department: Optional[str] = None
    key_metrics: dict[str, Any] = {}
    summary: Optional[str] = None
    recommendations: list[str] = []
    data_tables: list[dict[str, Any]] = []


class ValidationResult(BaseModel):
    is_valid: bool
    confidence: float
    errors: list[str] = []
    warnings: list[str] = []
    corrected_data: dict[str, Any] = {}


# ── Shared prompt templates ───────────────────────────────────────────────────

INVOICE_PROMPT = """Extract structured invoice data from the following text. Return ONLY valid JSON with no explanation.

Text:
{text}

Return JSON with exactly these fields:
{{
  "vendor_name": "string or null",
  "vendor_address": "string or null",
  "vendor_email": "string or null",
  "vendor_phone": "string or null",
  "gst_number": "15-char GST number or null",
  "pan_number": "10-char PAN or null",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "purchase_order_number": "string or null",
  "subtotal": number_or_null,
  "tax_amount": number_or_null,
  "discount_amount": number_or_null,
  "total_amount": number_or_null,
  "currency": "INR",
  "payment_terms": "string or null",
  "bank_account": "string or null",
  "ifsc_code": "string or null",
  "line_items": [{{"description":"str","quantity":num,"unit_price":num,"amount":num,"tax_rate":num,"hsn_code":"str"}}],
  "tax_breakdown": {{"cgst":num,"sgst":num,"igst":num}},
  "confidence": 0.0_to_1.0
}}"""

CONTRACT_PROMPT = """Extract structured contract data from the text below. Return ONLY valid JSON.

Text:
{text}

Return JSON:
{{
  "parties": [{{"name":"str","role":"buyer/seller/service_provider/client"}}],
  "contract_type": "string or null",
  "contract_value": number_or_null,
  "currency": "INR",
  "effective_date": "YYYY-MM-DD or null",
  "expiration_date": "YYYY-MM-DD or null",
  "signed_date": "YYYY-MM-DD or null",
  "obligations": ["obligation 1"],
  "penalties": [{{"description":"str","amount":num,"trigger":"str"}}],
  "renewal_clauses": ["clause 1"],
  "risk_clauses": ["clause 1"],
  "termination_clauses": ["clause 1"],
  "payment_terms": {{"schedule":"str","method":"str"}},
  "sla_terms": {{"uptime":"str","response_time":"str"}},
  "risk_score": 0.0_to_1.0,
  "risk_factors": ["factor 1"],
  "summary": "brief summary",
  "key_terms": {{"jurisdiction":"str","governing_law":"str"}}
}}"""

VALIDATION_PROMPT = """Validate the following extracted document data. Return ONLY valid JSON.

Data:
{data}

Check for: missing required fields, invalid dates, math errors
(subtotal+tax not equal total), invalid GST format, negative/zero amounts.

Return JSON:
{{
  "is_valid": true_or_false,
  "confidence": 0.0_to_1.0,
  "errors": ["error 1"],
  "warnings": ["warning 1"],
  "corrected_data": {{}}
}}"""

SQL_PROMPT = """Generate a PostgreSQL-compatible SELECT query for this question using the schema below.
Return ONLY the SQL — no explanation, no markdown.

Schema:
{schema}

Question: {question}

Rules: SELECT only, max 1000 rows, use aliases, aggregate where appropriate."""

INSIGHTS_PROMPT = """Analyze this business data and give 3-5 concise actionable insights in bullet points.
Focus on trends, anomalies, cost opportunities, and risk. Max 200 words.

Data:
{data}"""


# ── Helper ────────────────────────────────────────────────────────────────────


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {}


def _regex_invoice(text: str) -> InvoiceExtraction:
    result = InvoiceExtraction()
    if m := re.search(r"invoice\s*(?:no|number|#)[:\s]*([A-Z0-9\-/]+)", text, re.IGNORECASE):
        result.invoice_number = m.group(1).strip()
    if m := re.search(r"total\s*(?:amount)?[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)", text, re.IGNORECASE):
        result.total_amount = float(m.group(1).replace(",", ""))
    if m := re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b", text):
        result.gst_number = m.group()
    if m := re.search(r"(?:invoice\s+date|date)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text, re.IGNORECASE):
        result.invoice_date = m.group(1)
    if m := re.search(r"(?:vendor|from|billed\s+by)[:\s]*([A-Za-z][\w\s&.,]{2,50})", text, re.IGNORECASE):
        result.vendor_name = m.group(1).strip()
    result.confidence = 0.4
    return result


# ── Claude backend ────────────────────────────────────────────────────────────


class ClaudeBackend:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
            except Exception as e:
                logger.error(f"Failed to init Anthropic client: {e}")
        return self._client

    def _call(self, prompt: str, max_tokens: int = 2048) -> str:
        client = self._get_client()
        if not client:
            return ""
        msg = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text if msg.content else ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_invoice(self, text: str) -> InvoiceExtraction:
        raw = self._call(INVOICE_PROMPT.format(text=text[:4000]))
        if not raw:
            return _regex_invoice(text)
        data = _parse_json(raw)
        try:
            return InvoiceExtraction(**data)
        except Exception:
            return _regex_invoice(text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_contract(self, text: str) -> ContractExtraction:
        raw = self._call(CONTRACT_PROMPT.format(text=text[:4000]))
        data = _parse_json(raw)
        try:
            return ContractExtraction(**data)
        except Exception:
            return ContractExtraction(summary=text[:300])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_sql(self, question: str, schema: str) -> str:
        raw = self._call(SQL_PROMPT.format(schema=schema, question=question), max_tokens=512)
        sql = re.sub(r"```sql\s*|```\s*", "", raw).strip()
        return sql or "SELECT * FROM invoices LIMIT 10"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_insights(self, data: dict) -> str:
        raw = self._call(INSIGHTS_PROMPT.format(data=json.dumps(data, default=str)[:3000]), max_tokens=512)
        return raw.strip() or "Unable to generate insights."

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def validate_extraction(self, data: dict) -> ValidationResult:
        raw = self._call(VALIDATION_PROMPT.format(data=json.dumps(data, default=str)[:2000]))
        result = _parse_json(raw)
        try:
            return ValidationResult(**result)
        except Exception:
            return ValidationResult(is_valid=True, confidence=0.5)


# ── Gemini backend ────────────────────────────────────────────────────────────


class GeminiBackend:
    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                import google.generativeai as genai

                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
            except Exception as e:
                logger.error(f"Failed to init Gemini: {e}")
        return self._model

    def _call(self, prompt: str) -> str:
        model = self._get_model()
        if not model:
            return ""
        try:
            return model.generate_content(prompt).text
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_invoice(self, text: str) -> InvoiceExtraction:
        raw = self._call(INVOICE_PROMPT.format(text=text[:4000]))
        data = _parse_json(raw)
        try:
            return InvoiceExtraction(**data)
        except Exception:
            return _regex_invoice(text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_contract(self, text: str) -> ContractExtraction:
        raw = self._call(CONTRACT_PROMPT.format(text=text[:4000]))
        data = _parse_json(raw)
        try:
            return ContractExtraction(**data)
        except Exception:
            return ContractExtraction(summary=text[:300])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_sql(self, question: str, schema: str) -> str:
        raw = self._call(SQL_PROMPT.format(schema=schema, question=question))
        return re.sub(r"```sql\s*|```\s*", "", raw).strip() or "SELECT * FROM invoices LIMIT 10"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_insights(self, data: dict) -> str:
        raw = self._call(INSIGHTS_PROMPT.format(data=json.dumps(data, default=str)[:3000]))
        return raw.strip() or "Unable to generate insights."

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def validate_extraction(self, data: dict) -> ValidationResult:
        raw = self._call(VALIDATION_PROMPT.format(data=json.dumps(data, default=str)[:2000]))
        result = _parse_json(raw)
        try:
            return ValidationResult(**result)
        except Exception:
            return ValidationResult(is_valid=True, confidence=0.5)


# ── Unified AIService facade ──────────────────────────────────────────────────


class AIService:
    """
    Selects the active backend at startup:
      1. Claude  — when CLAUDE_API_KEY is set
      2. Gemini  — when GEMINI_API_KEY is set
      3. Regex   — silent fallback (no API key required)
    """

    def __init__(self) -> None:
        if settings.CLAUDE_API_KEY:
            self._backend: ClaudeBackend | GeminiBackend = ClaudeBackend()
            logger.info("AI backend: Claude (%s)", settings.CLAUDE_MODEL)
        elif settings.GEMINI_API_KEY:
            self._backend = GeminiBackend()
            logger.info("AI backend: Gemini (%s)", settings.GEMINI_MODEL)
        else:
            self._backend = None  # type: ignore[assignment]
            logger.warning("AI backend: regex-only (set CLAUDE_API_KEY or GEMINI_API_KEY for full extraction)")

    # Public async wrappers (extraction_service calls these)

    async def extract_invoice_data(self, text: str) -> InvoiceExtraction:
        if self._backend is None:
            return _regex_invoice(text)
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, self._backend.extract_invoice, text)

    async def extract_contract_data(self, text: str) -> ContractExtraction:
        if self._backend is None:
            return ContractExtraction(summary=text[:300])
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, self._backend.extract_contract, text)

    async def generate_sql(self, question: str, schema: str) -> str:
        if self._backend is None:
            return "SELECT * FROM invoices LIMIT 10"
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, self._backend.generate_sql, question, schema)

    async def generate_insights(self, data: dict) -> str:
        if self._backend is None:
            return "Configure CLAUDE_API_KEY or GEMINI_API_KEY to enable AI insights."
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, self._backend.generate_insights, data)

    async def validate_extraction(self, data: dict) -> ValidationResult:
        if self._backend is None:
            return ValidationResult(is_valid=True, confidence=0.5)
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, self._backend.validate_extraction, data)

    # Legacy alias so existing code calling gemini_service.* still works
    async def extract_report_data(self, text: str) -> ReportExtraction:
        return ReportExtraction(summary=text[:300])


# Singleton — imported everywhere as `gemini_service` for backwards compat
gemini_service = AIService()
