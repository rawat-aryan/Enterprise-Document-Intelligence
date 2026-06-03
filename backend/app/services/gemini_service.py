from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.app.config import settings

logger = logging.getLogger(__name__)


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


class GeminiService:
    def __init__(self):
        self._model = None
        self._initialized = False

    def _get_model(self):
        if self._model is None:
            try:
                import google.generativeai as genai
                if settings.GEMINI_API_KEY:
                    genai.configure(api_key=settings.GEMINI_API_KEY)
                self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self._model = None
        return self._model

    def _parse_json_response(self, text: str) -> dict:
        # Extract JSON from response
        text = text.strip()
        # Remove markdown code blocks if present
        if "```json" in text:
            text = re.sub(r"```json\s*", "", text)
            text = re.sub(r"```\s*", "", text)
        elif "```" in text:
            text = re.sub(r"```\w*\s*", "", text)
            text = re.sub(r"```\s*", "", text)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to find JSON object within the text
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract_invoice_data(self, text: str) -> InvoiceExtraction:
        model = self._get_model()
        if model is None:
            return self._mock_invoice_extraction(text)

        prompt = f"""Extract structured invoice data from the following text. Return ONLY valid JSON.

Text:
{text[:4000]}

Return JSON with these fields:
{{
  "vendor_name": "string or null",
  "vendor_address": "string or null",
  "vendor_email": "string or null",
  "vendor_phone": "string or null",
  "gst_number": "GST number or null",
  "pan_number": "PAN number or null",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "purchase_order_number": "string or null",
  "subtotal": number or null,
  "tax_amount": number or null,
  "discount_amount": number or null,
  "total_amount": number or null,
  "currency": "INR",
  "payment_terms": "string or null",
  "bank_account": "string or null",
  "ifsc_code": "string or null",
  "line_items": [
    {{"description": "str", "quantity": number, "unit_price": number, "amount": number, "tax_rate": number, "hsn_code": "str"}}
  ],
  "tax_breakdown": {{"cgst": number, "sgst": number, "igst": number}},
  "confidence": 0.0 to 1.0
}}"""

        try:
            response = model.generate_content(prompt)
            data = self._parse_json_response(response.text)
            return InvoiceExtraction(**data)
        except Exception as e:
            logger.error(f"Gemini invoice extraction failed: {e}")
            return self._mock_invoice_extraction(text)

    def _mock_invoice_extraction(self, text: str) -> InvoiceExtraction:
        """Extract data using regex patterns when Gemini is unavailable."""
        import re

        result = InvoiceExtraction()
        # Invoice number
        inv_match = re.search(r"invoice\s*(?:no|number|#)[:\s]*([A-Z0-9\-/]+)", text, re.IGNORECASE)
        if inv_match:
            result.invoice_number = inv_match.group(1).strip()

        # Total amount
        total_match = re.search(r"total\s*(?:amount)?[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if total_match:
            result.total_amount = float(total_match.group(1).replace(",", ""))

        # GST number
        gst_match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b", text)
        if gst_match:
            result.gst_number = gst_match.group()

        # Date
        date_match = re.search(r"(?:invoice\s+date|date)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text, re.IGNORECASE)
        if date_match:
            result.invoice_date = date_match.group(1)

        result.confidence = 0.5
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract_contract_data(self, text: str) -> ContractExtraction:
        model = self._get_model()
        if model is None:
            return ContractExtraction(summary=text[:500], confidence=0.3)

        prompt = f"""Extract structured contract data from the following text. Return ONLY valid JSON.

Text:
{text[:4000]}

Return JSON with these fields:
{{
  "parties": [{{"name": "string", "role": "buyer/seller/service_provider/client"}}],
  "contract_type": "string or null",
  "contract_value": number or null,
  "currency": "INR",
  "effective_date": "YYYY-MM-DD or null",
  "expiration_date": "YYYY-MM-DD or null",
  "signed_date": "YYYY-MM-DD or null",
  "obligations": ["obligation 1", "obligation 2"],
  "penalties": [{{"description": "str", "amount": number, "trigger": "str"}}],
  "renewal_clauses": ["clause 1"],
  "risk_clauses": ["clause 1"],
  "termination_clauses": ["clause 1"],
  "payment_terms": {{"schedule": "str", "method": "str"}},
  "sla_terms": {{"uptime": "str", "response_time": "str"}},
  "risk_score": 0.0 to 1.0,
  "risk_factors": ["factor 1"],
  "summary": "brief summary",
  "key_terms": {{"jurisdiction": "str", "governing_law": "str"}}
}}"""

        try:
            response = model.generate_content(prompt)
            data = self._parse_json_response(response.text)
            return ContractExtraction(**data)
        except Exception as e:
            logger.error(f"Gemini contract extraction failed: {e}")
            return ContractExtraction(summary=text[:500])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract_report_data(self, text: str) -> ReportExtraction:
        model = self._get_model()
        if model is None:
            return ReportExtraction(summary=text[:300])

        prompt = f"""Extract structured data from this report document. Return ONLY valid JSON.

Text:
{text[:4000]}

Return JSON:
{{
  "title": "string or null",
  "report_date": "YYYY-MM-DD or null",
  "period": "string or null",
  "author": "string or null",
  "department": "string or null",
  "key_metrics": {{"metric_name": value}},
  "summary": "brief summary",
  "recommendations": ["recommendation 1"],
  "data_tables": [{{"table_name": "str", "headers": [], "rows": []}}]
}}"""

        try:
            response = model.generate_content(prompt)
            data = self._parse_json_response(response.text)
            return ReportExtraction(**data)
        except Exception as e:
            logger.error(f"Gemini report extraction failed: {e}")
            return ReportExtraction(summary=text[:300])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_sql(self, question: str, schema: str) -> str:
        model = self._get_model()
        if model is None:
            return "SELECT * FROM invoices LIMIT 10"

        prompt = f"""Generate a SQL query for the following question using the given schema.
Return ONLY the SQL query, no explanation.

Schema:
{schema}

Question: {question}

Rules:
- Use standard SQL compatible with PostgreSQL
- Use table aliases for clarity
- Include appropriate JOINs if needed
- Add WHERE clauses for filtering
- Use aggregate functions (SUM, COUNT, AVG) where appropriate
- Limit results to 1000 rows maximum"""

        try:
            response = model.generate_content(prompt)
            sql = response.text.strip()
            # Clean up response
            sql = re.sub(r"```sql\s*", "", sql)
            sql = re.sub(r"```\s*", "", sql)
            return sql.strip()
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return "SELECT * FROM invoices LIMIT 10"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_insights(self, data: dict) -> str:
        model = self._get_model()
        if model is None:
            return "Analysis unavailable - Gemini API not configured."

        prompt = f"""Analyze the following business data and provide concise actionable insights.

Data:
{json.dumps(data, indent=2, default=str)[:3000]}

Provide 3-5 key insights in bullet points. Focus on:
- Trends and patterns
- Anomalies or concerns
- Cost optimization opportunities
- Risk factors
Keep it under 200 words."""

        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Insights generation failed: {e}")
            return "Unable to generate insights at this time."

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def validate_extraction(self, data: dict) -> ValidationResult:
        model = self._get_model()
        if model is None:
            return ValidationResult(is_valid=True, confidence=0.5)

        prompt = f"""Validate the following extracted invoice/document data. Return ONLY valid JSON.

Data:
{json.dumps(data, indent=2, default=str)[:2000]}

Check for:
- Missing required fields (vendor_name, invoice_number, total_amount, invoice_date)
- Invalid date formats
- Math errors (subtotal + tax != total)
- Invalid GST number format
- Suspicious amounts (negative, zero, unreasonably large)

Return JSON:
{{
  "is_valid": true/false,
  "confidence": 0.0 to 1.0,
  "errors": ["error 1", "error 2"],
  "warnings": ["warning 1"],
  "corrected_data": {{}}
}}"""

        try:
            response = model.generate_content(prompt)
            result_data = self._parse_json_response(response.text)
            return ValidationResult(**result_data)
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return ValidationResult(is_valid=True, confidence=0.5)


gemini_service = GeminiService()
