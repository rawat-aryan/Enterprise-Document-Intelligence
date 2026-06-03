"""
Airflow DAG: Bulk Invoice Processing Pipeline
Processes batches of invoices from database, runs duplicate detection, validates, and notifies.
"""

from __future__ import annotations

from datetime import timedelta

from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from airflow import DAG

default_args = {
    "owner": "accounts-payable",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": True,
    "execution_timeout": timedelta(hours=2),
}


def fetch_pending_invoices(**context) -> list[str]:
    """Fetch invoice IDs pending duplicate detection."""
    import asyncio
    import logging
    import sys

    sys.path.insert(0, "/app")
    logger = logging.getLogger(__name__)

    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from backend.app.config import settings
        from backend.app.models.invoice import Invoice, ValidationStatus

        async def fetch():
            engine = create_async_engine(settings.DATABASE_URL)
            Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with Session() as session:
                result = await session.execute(
                    select(Invoice.id).where(Invoice.validation_status == ValidationStatus.PENDING.value).limit(500)
                )
                ids = [row[0] for row in result.all()]
            await engine.dispose()
            return ids

        invoice_ids = asyncio.run(fetch())
        logger.info(f"Found {len(invoice_ids)} pending invoices")
        context["task_instance"].xcom_push(key="invoice_ids", value=invoice_ids)
        return invoice_ids
    except Exception as e:
        logger.error(f"Failed to fetch invoices: {e}")
        return []


def run_duplicate_detection(**context) -> dict:
    """Run duplicate detection on pending invoices."""
    import asyncio
    import logging
    import sys

    sys.path.insert(0, "/app")
    logger = logging.getLogger(__name__)

    invoice_ids = context["task_instance"].xcom_pull(key="invoice_ids", task_ids="fetch_pending_invoices")
    if not invoice_ids:
        return {"processed": 0, "duplicates": 0}

    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from backend.app.config import settings
        from backend.app.models.invoice import Invoice
        from backend.app.services.duplicate_detection_service import duplicate_detection_service

        async def process():
            engine = create_async_engine(settings.DATABASE_URL)
            Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            duplicates_found = 0

            async with Session() as session:
                for inv_id in invoice_ids:
                    result = await session.execute(select(Invoice).where(Invoice.id == inv_id))
                    invoice = result.scalar_one_or_none()
                    if not invoice:
                        continue
                    dup_result = await duplicate_detection_service.check_duplicate(invoice, session)
                    if dup_result.is_duplicate:
                        invoice.is_duplicate = True
                        invoice.duplicate_of = dup_result.duplicate_of
                        invoice.duplicate_score = dup_result.risk_score
                        duplicates_found += 1
                await session.commit()
            await engine.dispose()
            return duplicates_found

        dups = asyncio.run(process())
        result = {"processed": len(invoice_ids), "duplicates": dups}
        context["task_instance"].xcom_push(key="dup_result", value=result)
        logger.info(f"Duplicate detection: {result}")
        return result
    except Exception as e:
        logger.error(f"Duplicate detection failed: {e}")
        return {"processed": 0, "duplicates": 0, "error": str(e)}


def run_validation(**context) -> dict:
    """Run validation on processed invoices."""
    import asyncio
    import logging
    import sys

    sys.path.insert(0, "/app")
    logger = logging.getLogger(__name__)

    invoice_ids = context["task_instance"].xcom_pull(key="invoice_ids", task_ids="fetch_pending_invoices")
    if not invoice_ids:
        return {"validated": 0, "invalid": 0}

    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from backend.app.config import settings
        from backend.app.models.invoice import Invoice
        from backend.app.services.validation_service import validation_service

        async def validate():
            engine = create_async_engine(settings.DATABASE_URL)
            Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            validated = 0
            invalid = 0

            async with Session() as session:
                for inv_id in invoice_ids:
                    result = await session.execute(select(Invoice).where(Invoice.id == inv_id))
                    invoice = result.scalar_one_or_none()
                    if not invoice:
                        continue
                    report = validation_service.validate_invoice(invoice)
                    invoice = validation_service.apply_validation(invoice, report)
                    if report.is_valid:
                        validated += 1
                    else:
                        invalid += 1
                await session.commit()
            await engine.dispose()
            return validated, invalid

        v, i = asyncio.run(validate())
        logger.info(f"Validation: {v} valid, {i} invalid")
        return {"validated": v, "invalid": i}
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {"validated": 0, "invalid": 0, "error": str(e)}


def send_processing_summary(**context):
    """Log processing summary (in prod would send email/Slack)."""
    import logging

    logger = logging.getLogger(__name__)

    dup_result = context["task_instance"].xcom_pull(key="dup_result", task_ids="duplicate_detection")
    val_result = context["task_instance"].xcom_pull(task_ids="validation")

    summary = {
        "run_date": str(context.get("execution_date")),
        "duplicates_found": dup_result.get("duplicates", 0) if dup_result else 0,
        "invoices_validated": val_result.get("validated", 0) if val_result else 0,
        "invoices_invalid": val_result.get("invalid", 0) if val_result else 0,
    }
    logger.info(f"Processing summary: {summary}")
    return summary


with DAG(
    dag_id="invoice_bulk_processing",
    description="Bulk invoice duplicate detection, validation, and notification pipeline",
    default_args=default_args,
    schedule_interval="0 */4 * * *",  # Every 4 hours
    catchup=False,
    max_active_runs=1,
    tags=["invoices", "ap-automation"],
) as dag:

    start = DummyOperator(task_id="start")

    fetch_invoices = PythonOperator(
        task_id="fetch_pending_invoices",
        python_callable=fetch_pending_invoices,
        provide_context=True,
    )

    dedup = PythonOperator(
        task_id="duplicate_detection",
        python_callable=run_duplicate_detection,
        provide_context=True,
    )

    validate = PythonOperator(
        task_id="validation",
        python_callable=run_validation,
        provide_context=True,
    )

    summary = PythonOperator(
        task_id="processing_summary",
        python_callable=send_processing_summary,
        provide_context=True,
    )

    end = DummyOperator(task_id="end")

    start >> fetch_invoices >> dedup >> validate >> summary >> end
