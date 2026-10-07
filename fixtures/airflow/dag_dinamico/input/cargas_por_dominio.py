"""Fixture sintetica: DAG montado em laco -- fora do alcance da leitura estatica."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

for dominio in ("clientes", "pedidos"):
    with DAG(
        dag_id=f"carga_{dominio}",
        schedule="0 7 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
    ) as dag:
        GlueJobOperator(task_id="carga", job_name=f"carga-{dominio}")
