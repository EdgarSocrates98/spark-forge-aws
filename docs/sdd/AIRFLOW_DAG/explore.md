---
sdd: 1
feature: AIRFLOW_DAG
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Extrator do DAG .py por AST (molde de sparkforge/facts/pyspark_ast.py): af.dag, af.task, af.dependency e af.unresolved; verbo sparkforge analyze airflow-dag e tool MCP; area SF-AIRFLOW com quatro regras que julgam o DAG (wait_for_completion False com downstream; stop_job_run_on_kill False com execution_timeout; deferrable False com espera sincrona; duas camadas de retry cruzando com aws_glue_job pelo job_name literal, derivacao em fuse como o sfn.glue_job_link); coordenador glue-infra-reviewer com rota por findings_area."
    tradeoffs:
      - "mesmo desenho do STEP_FUNCTIONS, que acabou de passar pelas tres portas do criterio"
      - "a regra de maior valor (duas camadas de retry) so existe cruzando os dois artefatos"
      - "DAG gerado dinamicamente (laco, factory, import de modulo) nao e legivel por AST e sai af.unresolved nomeado"
  - id: B
    summary: "A sem o cruzamento: so as tres regras que o DAG sozinho sustenta."
    tradeoffs:
      - "menor, e entrega o dominio pelas tres portas do mesmo jeito"
      - "deixa de fora a regra que o operador mais sente (retry que multiplica execucao de job batch)"
  - id: C
    summary: "A mais dependencia entre DAGs (ExternalTaskSensor, TriggerDagRunOperator) e o risco de espera entre eles."
    tradeoffs:
      - "cobre o modo de falha mais caro de plataforma com muitos DAGs"
      - "exige ler varios arquivos e casar dag_id entre eles; dobra o tamanho"
chosen: A
---

# AIRFLOW_DAG — exploração

## Origem

Segundo domínio pela porta do critério, depois do STEP_FUNCTIONS (#90). Pedido do
operador em 2026-09-19: "Airflow pela mesma porta".

## Perfil

`dev`.

## O que o repositório tem hoje

- `knowledge/airflow-pipelines.md`: 56 palavras de princípio, sem regra e sem extrator.
  Ele cita `https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html`.
- Nenhum fact de Airflow. O molde de leitura de Python por AST é
  `sparkforge/facts/pyspark_ast.py`; o molde de domínio novo inteiro é
  `sparkforge/facts/stepfunctions.py` com a derivação em `fuse`.
- A área `SF-AIRFLOW` existiu como área de coordenação oca e saiu no SF_STUBS (#88). O
  nome volta agora com regra que julga.

## Fontes lidas (2026-09-19)

- `https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/operators/glue/index.html`,
  parâmetros do `GlueJobOperator` e seus defaults:
  - `wait_for_completion` (default `True`): "Whether to wait for job run completion";
  - `deferrable` (default `False`): "If True, the operator will wait asynchronously for
    the job to complete";
  - `stop_job_run_on_kill` (default `False`): "If True, Operator will stop the job run
    when task is killed";
  - `job_poll_interval` (default `6`), `verbose` (default `False`),
    `update_config` (default `False`), `job_name` (default `aws_glue_default_job`).
- `https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html`:
  - `core.default_task_retries`, default `0`: "The number of retries each task is going to
    have by default";
  - `core.default_task_retry_delay`, default `300`;
  - `core.default_task_execution_timeout`, default vazio.
- `https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html`:
  "If you want a task to have a maximum runtime, set its `execution_timeout` attribute to
  a `datetime.timedelta` value that is the maximum permissible runtime." A página **não**
  publica o número default de `retries`; quem publica é a referência de configuração.
- Do lado do Glue, as frases já citadas em `docs/sdd/STEP_FUNCTIONS/explore.md`:
  `MaxRetries` é da definição do job, e o `StartJobRun` não o sobrescreve.

## Perguntas feitas

1. Qual escopo? Resposta (2026-09-19): A, DAG mais o cruzamento com o job Glue.

## Abordagens

A (recomendada) repete o desenho que o STEP_FUNCTIONS validou. B abre mão da regra de
maior valor. C dobra o tamanho para cobrir dependência entre DAGs.

## Escolha

A, escolhida pelo operador.
