# Airflow e Pipelines

Trate tasks como transacoes. Resultados parciais nao devem parecer completos; tasks devem ser idempotentes em retries. Leia e escreva particoes especificas, use XCom para mensagens pequenas e S3 para dados grandes. Evite codigo pesado no top-level do DAG.

Valide data_interval, retries, backfill, pools, sensores, datasets, secrets, timeouts, alertas e reexecucao.

Os defaults do `GlueJobOperator` — `wait_for_completion`, `deferrable` e
`stop_job_run_on_kill` — e o `retries` do Airflow estão com a frase citada e a data de
leitura em [`knowledge/airflow/glue-operator.md`](airflow/glue-operator.md), que é o que
as regras `SF-AIRFLOW` consomem. Este arquivo guarda princípio; aquele guarda fonte.

Fonte: https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html
