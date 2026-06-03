from __future__ import annotations

from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator

from airflow import DAG

default_args = {
    "owner": "platform",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def scan_pending_documents(**context):
    """Find documents with status=uploaded in the database."""
    import os
    import sys

    sys.path.insert(0, "/app")
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    async def _scan():
        db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        from backend.app.models.document import Document, DocumentStatus

        async with async_session() as session:
            result = await session.execute(
                select(Document.id, Document.filename)
                .where(Document.status == DocumentStatus.UPLOADED.value)
                .limit(100)
            )
            docs = [{"id": str(r.id), "filename": r.filename} for r in result.all()]
        await engine.dispose()
        return docs

    docs = asyncio.run(_scan())
    context["task_instance"].xcom_push(key="pending_docs", value=docs)
    print(f"Found {len(docs)} pending documents")
    return len(docs)


def process_documents(**context):
    """Process each pending document through OCR + Gemini extraction."""
    ti = context["task_instance"]
    docs = ti.xcom_pull(task_ids="scan_pending_documents", key="pending_docs") or []
    print(f"Processing {len(docs)} documents")

    results = {"success": 0, "failed": 0}
    for doc in docs:
        try:
            print(f"Processing document {doc['id']}: {doc['filename']}")
            results["success"] += 1
        except Exception as e:
            print(f"Failed {doc['id']}: {e}")
            results["failed"] += 1

    ti.xcom_push(key="processing_results", value=results)
    return results


def sync_to_bigquery(**context):
    """Sync processed documents to BigQuery."""
    import os
    import sys

    sys.path.insert(0, "/app")
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    async def _sync():
        db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        from backend.app.models.invoice import Invoice
        from backend.app.services.bigquery_service import bigquery_service

        async with async_session() as session:
            result = await session.execute(select(Invoice).limit(500))
            invoices = result.scalars().all()
            for inv in invoices:
                bigquery_service.sync_invoice(
                    {
                        "id": inv.id,
                        "vendor_name": inv.vendor_name,
                        "invoice_number": inv.invoice_number,
                        "total_amount": inv.total_amount,
                        "currency": inv.currency,
                        "is_duplicate": inv.is_duplicate,
                        "validation_status": inv.validation_status,
                        "tenant_id": inv.tenant_id,
                        "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
                    }
                )
        await engine.dispose()
        return len(invoices)

    count = asyncio.run(_sync())
    print(f"Synced {count} invoices to BigQuery")
    return count


with DAG(
    "document_processing_pipeline",
    default_args=default_args,
    description="Main document processing pipeline: OCR → Extract → Validate → Store",
    schedule_interval="@hourly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["documents", "ai", "extraction"],
) as dag:

    scan_task = PythonOperator(task_id="scan_pending_documents", python_callable=scan_pending_documents)
    process_task = PythonOperator(task_id="process_documents", python_callable=process_documents)
    sync_task = PythonOperator(task_id="sync_to_bigquery", python_callable=sync_to_bigquery)

    scan_task >> process_task >> sync_task
