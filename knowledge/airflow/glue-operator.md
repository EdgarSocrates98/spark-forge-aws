# GlueJobOperator do Airflow: espera, prazo, forma de esperar e retry

> **Lido em 2026-09-20.** Três páginas oficiais do Apache Airflow — uma do provider
> Amazon e duas do core — mais as duas páginas da API do AWS Glue já citadas em
> `knowledge/stepfunctions/glue-integration.md`. Quem consome: o extrator
> `sparkforge/facts/airflow_dag.py` (os defaults publicados moram lá, com a URL ao
> lado) e as quatro regras de `rules/catalog/airflow.yaml`. Frase entre aspas é
> citação literal; o resto é leitura nossa, e diz de qual frase veio.

## 1. Os três parâmetros do operador que decidem o que acontece com o job

Da página do `GlueJobOperator` no provider Amazon:

| parâmetro | default publicado | o que a documentação diz |
|---|---|---|
| `wait_for_completion` | `True` | "Whether to wait for job run completion" |
| `deferrable` | `False` | "If True, the operator will wait asynchronously for the job to complete" |
| `stop_job_run_on_kill` | `False` | "If True, Operator will stop the job run when task is killed" |
| `job_poll_interval` | `6` | intervalo entre consultas ao job |
| `job_name` | `aws_glue_default_job` | nome do job Glue a disparar |

Leitura nossa, a partir das três primeiras linhas: **nenhum dos três aparece no código
PySpark nem no event log do job.** Eles moram no arquivo do DAG, e é por isso que o
SparkForge o lê.

## 2. O prazo da task, e o que o core publica

- `execution_timeout` (core-concepts/tasks): "If you want a task to have a maximum
  runtime, set its `execution_timeout` attribute to a `datetime.timedelta` value that
  is the maximum permissible runtime." A mesma página **não** publica o default de
  `retries`.
- `core.default_task_retries`, default `0` (configurations-ref): "The number of retries
  each task is going to have by default". `core.default_task_retry_delay` é `300`, e
  `core.default_task_execution_timeout` é vazio.

Leitura nossa: um DAG que não escreve `retries` em lugar nenhum tem `retries` efetivo
`0`, e por isso a `SF-AIRFLOW-004` não dispara sobre DAG que nunca pediu retentativa.

## 3. O lado do Glue

- `MaxRetries`: "The maximum number of times to retry this job after a JobRun fails."
  (aws-glue-api-jobs-job).
- Os parâmetros de `StartJobRun` não incluem `MaxRetries` (aws-glue-api-jobs-runs):
  leitura nossa — o Airflow não o sobrescreve ao disparar.

## 4. O que cada regra afirma, e o que ela não afirma

| regra | afirma | não afirma |
|---|---|---|
| SF-AIRFLOW-001 | `wait_for_completion=False` com tarefa a jusante: a próxima roda com o job em execução | que o job vai falhar |
| SF-AIRFLOW-002 | prazo declarado com `stop_job_run_on_kill` ausente ou `False`: o operador não para o JobRun | o que acontece com o JobRun depois disso (lacuna 2) |
| SF-AIRFLOW-003 | espera síncrona: o slot de worker fica ocupado pelo tempo do job | que falta slot no ambiente — isso é medida do Airflow, e não está aqui |
| SF-AIRFLOW-004 | as duas camadas de retry existem sobre o mesmo job | quantas vezes o job roda numa falha (lacuna 1) |

O vínculo da SF-AIRFLOW-004 é por `job_name` literal igual ao `name` do `aws_glue_job`,
feito em `fuse`. Nome em `{{ jinja }}`, variável, f-string e job ausente do Terraform
saem em `af.unresolved` com a razão, nunca como vínculo.

## 5. Lacunas nomeadas

1. **Composição dos retries.** Nenhuma das duas documentações descreve como o `retries`
   do Airflow compõe com o `MaxRetries` do Glue. Cada retentativa da task é um
   `StartJobRun` novo, e o retry do Glue é outro JobRun. O que destrava afirmar a
   contagem de tentativas: os JobRuns do intervalo de uma falha real
   (`sparkforge collect glue-job-runs`) ao lado do histórico da task.
2. **JobRun quando a task é morta com `stop_job_run_on_kill` False.** A documentação do
   provider diz o que o parâmetro faz quando é `True`, e não descreve o que acontece
   com o JobRun quando é `False` e a task é morta (U3 de
   `docs/sdd/AIRFLOW_DAG/define.md`). A regra afirma o que a documentação sustenta — o
   operador não para o job — e não afirma o que o Glue faz depois.
3. **Triggerer.** A espera diferida (`deferrable=True`) precisa de um processo
   `triggerer` no ambiente. **Nenhuma das três páginas lidas publica esse requisito**, e
   o arquivo do DAG não diz se o ambiente tem um: por isso a `SF-AIRFLOW-003` traz o
   ponto como `risks` e nenhum fact o afirma. O que destrava: ler a página de deferring
   do guia do Airflow e a página de versões do ambiente gerenciado em uso.
4. **DAG real não observado.** O corpus `fixtures/airflow/` é sintético, montado a
   partir dos exemplos da documentação do provider (U2 do `define`). Um DAG real do
   operador, lido na conversa e nunca commitado, é o que o testaria contra produção.
5. **O que a leitura estática não alcança.** DAG montado em laço ou por factory,
   TaskFlow API (`@task`, `@dag`) e argumento resolvido em execução (variável,
   f-string, `{{ jinja }}`) saem em `af.unresolved` nomeado. Importar o DAG para
   resolvê-los executaria código do operador, e o repositório não executa artefato.

## Fontes

- Provider Amazon — `GlueJobOperator`: `wait_for_completion`, `deferrable`, `stop_job_run_on_kill`, `job_poll_interval` e `job_name`, com os defaults. https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/operators/glue/index.html (retrieved 2026-09-20)
- Guia do Apache Airflow — referência de configuração: `core.default_task_retries`, `core.default_task_retry_delay` e `core.default_task_execution_timeout`. https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html (retrieved 2026-09-20)
- Guia do Apache Airflow — tasks: `execution_timeout`. https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html (retrieved 2026-09-20)
- API do AWS Glue — Jobs: `MaxRetries`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-job.html (retrieved 2026-09-19)
- API do AWS Glue — Job runs: os parâmetros de `StartJobRun`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html (retrieved 2026-09-19)
