from __future__ import annotations

from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator

from airflow import DAG

default_args = {
    "owner": "platform",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def refresh_vendor_analytics(**context):
    print("Refreshing vendor analytics in BigQuery...")
    return "done"


def generate_daily_recommendations(**context):
    print("Generating daily AI recommendations...")
    return "done"


with DAG(
    "bigquery_daily_sync",
    default_args=default_args,
    description="Daily BigQuery sync and analytics refresh",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["bigquery", "analytics"],
) as dag:

    refresh_task = PythonOperator(task_id="refresh_vendor_analytics", python_callable=refresh_vendor_analytics)
    reco_task = PythonOperator(task_id="generate_recommendations", python_callable=generate_daily_recommendations)

    refresh_task >> reco_task
