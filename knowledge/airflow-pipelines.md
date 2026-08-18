# Airflow e Pipelines

Trate tasks como transacoes. Resultados parciais nao devem parecer completos; tasks devem ser idempotentes em retries. Leia e escreva particoes especificas, use XCom para mensagens pequenas e S3 para dados grandes. Evite codigo pesado no top-level do DAG.

Valide data_interval, retries, backfill, pools, sensores, datasets, secrets, timeouts, alertas e reexecucao.

Fonte: https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html
