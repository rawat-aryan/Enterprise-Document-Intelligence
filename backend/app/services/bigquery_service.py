from __future__ import annotations

import logging
from typing import Any

from backend.app.config import settings

logger = logging.getLogger(__name__)


class BigQueryService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import bigquery

                self._client = bigquery.Client(project=settings.GOOGLE_PROJECT_ID)
            except Exception as e:
                logger.warning(f"BigQuery client unavailable: {e}")
        return self._client

    def insert_rows(self, table_id: str, rows: list[dict[str, Any]]) -> bool:
        client = self._get_client()
        if not client or not rows:
            return False
        try:
            full_table = f"{settings.GOOGLE_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{table_id}"
            errors = client.insert_rows_json(full_table, rows)
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
                return False
            return True
        except Exception as e:
            logger.error(f"BigQuery insert failed: {e}")
            return False

    def run_query(self, sql: str) -> list[dict[str, Any]]:
        client = self._get_client()
        if not client:
            return []
        try:
            job = client.query(sql)
            return [dict(row) for row in job.result()]
        except Exception as e:
            logger.error(f"BigQuery query failed: {e}")
            return []

    def sync_invoice(self, invoice_dict: dict) -> bool:
        row = {
            "invoice_id": invoice_dict.get("id"),
            "vendor_name": invoice_dict.get("vendor_name"),
            "invoice_number": invoice_dict.get("invoice_number"),
            "invoice_date": str(invoice_dict.get("invoice_date")) if invoice_dict.get("invoice_date") else None,
            "total_amount": invoice_dict.get("total_amount"),
            "tax_amount": invoice_dict.get("tax_amount"),
            "currency": invoice_dict.get("currency", "INR"),
            "validation_status": invoice_dict.get("validation_status"),
            "is_duplicate": invoice_dict.get("is_duplicate", False),
            "tenant_id": invoice_dict.get("tenant_id"),
        }
        return self.insert_rows("fact_invoices", [row])


bigquery_service = BigQueryService()
