<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_airflow_dag`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts do arquivo `.py` de um DAG do Apache Airflow. Le por AST e NUNCA importa nem executa o DAG. Emite `af.dag` (dag_id e schedule quando literais, e o `default_args` com `retries` e `execution_timeout`), um `af.task` por operador instanciado (classe, `task_id`, e para o `GlueJobOperator` o `job_name` literal, o EFETIVO de `wait_for_completion`/`deferrable`/`stop_job_run_on_kill` com a marca de omitido -- os defaults publicados sao True, False e False --, o `retries` efetivo e se `execution_timeout` esta declarado), `af.dependency` por elo declarado com `>>`, `<<`, `set_downstream` ou `set_upstream`, `af.unresolved` com a razao do que nao deu para ler (argumento nao literal, DAG montado em laco, TaskFlow, Python invalido), e a sentinela `af.analyzed`. Argumento que nao e literal NAO vira o default: o atributo sai ausente e a lacuna sai nomeada. Com o Terraform do job no mesmo pool, `sparkforge_fuse` liga a task ao `aws_glue_job` de mesmo nome.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo .py do DAG ou diretorio com eles. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze airflow-dag`](../cli/analyze.md)

## Capacidade

extract facts from an Apache Airflow DAG file

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
