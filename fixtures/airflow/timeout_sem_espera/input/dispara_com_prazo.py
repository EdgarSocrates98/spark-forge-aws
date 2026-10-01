"""Fixture sintetica: prazo declarado numa task que NAO espera o job."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="dispara_com_prazo",
    schedule="0 5 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    disparar = GlueJobOperator(
        task_id="disparar",
        job_name="carga-diaria",
        wait_for_completion=False,
        execution_timeout=timedelta(hours=2),
    )
