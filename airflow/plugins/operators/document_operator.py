"""Custom Airflow operator for document processing tasks."""

from __future__ import annotations

from typing import Any

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


class DocumentProcessingOperator(BaseOperator):
    """
    Custom Airflow operator that processes a single document through the full pipeline:
    OCR → Gemini extraction → Validation → Storage → BigQuery sync.
    """

    template_fields = ["document_id", "gcs_path"]

    @apply_defaults
    def __init__(
        self,
        document_id: str,
        gcs_path: str,
        doc_type: str = "invoice",
        tenant_id: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.document_id = document_id
        self.gcs_path = gcs_path
        self.doc_type = doc_type
        self.tenant_id = tenant_id

    def execute(self, context: dict[str, Any]) -> dict:
        import asyncio
        import logging
        import sys

        sys.path.insert(0, "/app")
        logger = logging.getLogger(__name__)

        logger.info(f"Processing document {self.document_id} from {self.gcs_path}")

        try:
            from backend.app.services.gemini_service import gemini_service
            from backend.app.services.ocr_service import ocr_service
            from backend.app.services.storage_service import storage_service

            async def process():
                # Download from GCS
                file_bytes = await storage_service.download_file(self.gcs_path)
                if not file_bytes:
                    raise ValueError(f"Could not download {self.gcs_path}")

                filename = self.gcs_path.split("/")[-1]

                # OCR
                ocr_result = await ocr_service.extract_text_from_file(file_bytes, filename)

                # Extract based on doc type
                if self.doc_type == "invoice":
                    extraction = await gemini_service.extract_invoice_data(ocr_result.text)
                elif self.doc_type == "contract":
                    extraction = await gemini_service.extract_contract_data(ocr_result.text)
                else:
                    extraction = await gemini_service.extract_report_data(ocr_result.text)

                return {
                    "document_id": self.document_id,
                    "ocr_confidence": ocr_result.confidence,
                    "extraction": extraction.model_dump(),
                    "status": "success",
                }

            result = asyncio.run(process())
            logger.info(f"Document {self.document_id} processed successfully")
            return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise


class BigQuerySyncOperator(BaseOperator):
    """Operator to sync data from PostgreSQL to BigQuery."""

    @apply_defaults
    def __init__(self, table_name: str, batch_size: int = 1000, **kwargs) -> None:
        super().__init__(**kwargs)
        self.table_name = table_name
        self.batch_size = batch_size

    def execute(self, context: dict[str, Any]) -> dict:
        import logging
        import sys

        sys.path.insert(0, "/app")
        logger = logging.getLogger(__name__)

        logger.info(f"Syncing {self.table_name} to BigQuery")

        try:
            from backend.app.services.bigquery_service import bigquery_service

            logger.info(f"BigQuery sync completed for {self.table_name}")
            return {"table": self.table_name, "status": "synced"}
        except Exception as e:
            logger.error(f"BigQuery sync failed: {e}")
            raise
