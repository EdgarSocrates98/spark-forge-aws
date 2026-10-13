"""Fixture sintetica: o Glue e disparado sem esperar, e a task seguinte depende dele."""
from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_diaria",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        wait_for_completion=False,
    )
    publicar = EmptyOperator(task_id="publicar")

    carga >> publicar
