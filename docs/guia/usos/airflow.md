# Airflow: como o DAG dispara o job Glue

O **Apache Airflow** dispara boa parte dos jobs Glue, e três defaults do
`GlueJobOperator` decidem o que acontece com o job sem aparecer no código PySpark nem no
event log: `wait_for_completion`, `deferrable` e `stop_job_run_on_kill`. Este manual
mostra como o SparkForge lê o arquivo `.py` do DAG e confere quatro coisas: se o fluxo
**espera** o job, se o Airflow **mata** a task deixando o job rodando, se a espera
**segura** um slot de worker, e — com o Terraform do job ao lado — se o **retry** existe
nas duas camadas.

O SparkForge **não importa e não executa** o DAG: ele o lê por AST. Todos os exemplos
usam arquivos sintéticos de `fixtures/airflow/`.

## Receita rápida

```bash
mkdir -p /tmp/af

# 1. Extrair os facts do DAG (arquivo .py ou a pasta de DAGs)
sparkforge analyze airflow-dag \
  --path fixtures/airflow/sem_espera/input --out /tmp/af/facts_airflow.json

# 2. Julgar: SF-AIRFLOW-001 a 003 leem so o DAG
sparkforge judge --facts /tmp/af/facts_airflow.json

# 3. Com o Terraform do job: extrair os dois lados, fundir e julgar
sparkforge analyze airflow-dag \
  --path fixtures/airflow/retry_duas_camadas/input --out /tmp/af/af.json
sparkforge analyze terraform \
  --path fixtures/airflow/retry_duas_camadas/input --out /tmp/af/tf.json
sparkforge fuse --facts /tmp/af/af.json --facts /tmp/af/tf.json --out /tmp/af/fundidos.json
sparkforge judge --facts /tmp/af/fundidos.json
```

## O que sai

| kind | um por | o que diz |
|---|---|---|
| `af.dag` | chamada `DAG(...)` | `dag_id` e `schedule` quando literais, e o `default_args` com `retries` e `execution_timeout` |
| `af.task` | operador instanciado | classe, `task_id`, `has_downstream`, e para o `GlueJobOperator` o `job_name` literal, o efetivo de `wait_for_completion`/`deferrable`/`stop_job_run_on_kill` com a marca de omitido, o `retries` efetivo e se `execution_timeout` está declarado |
| `af.dependency` | elo declarado | `>>`, `<<`, `set_downstream` ou `set_upstream`, com a forma que o declarou |
| `af.glue_job_link` | task ligada a um `aws_glue_job` (só em `fuse`) | o `retries` efetivo do Airflow e o `max_retries` do job |
| `af.unresolved` | o que não deu para ler ou ligar | a razão: argumento não literal, DAG em laço, TaskFlow, Python inválido, `job_name` dinâmico, job ausente do Terraform |
| `af.analyzed` | arquivo | as contagens — prova de que o arquivo foi lido |

**Argumento que não é literal nunca vira o default.** `wait_for_completion=ESPERA`,
`job_name=f"carga-{dominio}"` e `job_name="{{ var.value.job }}"` saem em `af.unresolved`
com a razão, e o atributo correspondente fica ausente — a regra então fica calada, em
vez de julgar um valor que ninguém leu.

## As quatro regras

| regra | dispara quando | severidade |
|---|---|---|
| `SF-AIRFLOW-001` | `wait_for_completion=False` e a task tem tarefa a jusante: a próxima roda com o job em execução | P2 |
| `SF-AIRFLOW-002` | a task espera o job, tem `execution_timeout` declarado (na task ou em `default_args`) e `stop_job_run_on_kill` ausente ou `False`: o Airflow mata a task e o operador não para o JobRun | P1 |
| `SF-AIRFLOW-003` | a task espera o job (default `True`) sem `deferrable` (default `False`): o slot de worker fica preso pelo tempo do job | P3 |
| `SF-AIRFLOW-004` | a task ligada ao job tem `retries` efetivo maior que zero e o job tem `max_retries` maior que zero | P2 |

A `SF-AIRFLOW-004` afirma só que as duas camadas existem. **Quantas vezes o job roda
numa falha não é documentado** — cada retentativa da task é um `StartJobRun` novo, e o
retry do Glue é outro JobRun. Medir exige os JobRuns do intervalo de uma falha real
(`sparkforge collect glue-job-runs`) ao lado do histórico da task.

## O que ele não faz

- Não importa nem executa o DAG, e por isso não resolve DAG montado em laço, por factory
  ou por import: sai `af.unresolved` com `dag_dinamico`.
- Não lê a TaskFlow API além de reconhecer `@dag`, `@task` e `@task_group` e nomear o
  que não leu (`taskflow_decorador`). Operador clássico instanciado **dentro** de uma
  função — o caso comum sob `@dag` — sai com razão própria, `operador_em_funcao`.
- Não lê metadado do Airflow em execução (task instances, duração, retentativas que
  aconteceram): isso exige acesso ao banco ou à API.
- Não lê dependência **entre DAGs** (`ExternalTaskSensor`, `TriggerDagRunOperator`).
- Não julga outros operadores (EMR, Athena, Lambda): o extrator os registra, e nenhuma
  regra os julga.

## Referência

- As frases citadas e as lacunas: [`knowledge/airflow/glue-operator.md`](../../../knowledge/airflow/glue-operator.md).
- As regras: [`rules/catalog/airflow.yaml`](../../../rules/catalog/airflow.yaml).
- O corpus: [`fixtures/airflow/`](../../../fixtures/airflow/).
