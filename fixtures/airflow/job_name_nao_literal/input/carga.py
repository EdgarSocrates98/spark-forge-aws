"""Fixture sintetica: o nome do job vem de uma Variable, resolvida em execucao."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_parametrizada",
    schedule="0 5 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 2},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="{{ var.value.glue_job }}",
        deferrable=True,
    )
