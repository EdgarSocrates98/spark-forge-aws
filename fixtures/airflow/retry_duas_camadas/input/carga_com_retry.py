"""Fixture sintetica: o mesmo job com retry no Airflow e no proprio Glue."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

DEFAULT_ARGS = {"retries": 2}

with DAG(
    dag_id="carga_com_retry",
    schedule="0 5 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        deferrable=True,
    )
