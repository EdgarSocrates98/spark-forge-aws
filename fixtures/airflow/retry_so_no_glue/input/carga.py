"""Fixture sintetica: o Airflow nao retenta; o job Glue retenta."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_sem_retry",
    schedule="0 5 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        deferrable=True,
    )
