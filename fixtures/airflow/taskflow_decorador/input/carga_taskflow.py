"""Fixture sintetica: TaskFlow API -- reconhecida e nomeada, nao lida."""
from datetime import datetime

from airflow.decorators import dag, task


@dag(schedule="0 8 * * *", start_date=datetime(2026, 1, 1), catchup=False)
def carga_taskflow():
    @task
    def extrair():
        return {"linhas": 0}

    extrair()


carga_taskflow()
