"""Fixture sintetica: o Airflow mata a task no prazo, e o JobRun continua."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_com_timeout",
    schedule="0 4 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        execution_timeout=timedelta(hours=2),
        deferrable=True,
    )
