"""Fixture sintetica: o negativo da area -- os tres argumentos escritos, e nenhum achado."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_limpa",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        wait_for_completion=True,
        deferrable=True,
        stop_job_run_on_kill=True,
    )
