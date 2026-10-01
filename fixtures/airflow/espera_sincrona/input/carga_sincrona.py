"""Fixture sintetica: tudo no default -- a espera segura um slot de worker."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_sincrona",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(task_id="carga", job_name="carga-diaria")
