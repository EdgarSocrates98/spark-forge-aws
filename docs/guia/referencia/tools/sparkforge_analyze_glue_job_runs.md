<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_glue_job_runs`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de historico do DIRETORIO de artefatos de run Glue: um `glue.job_run` por run, `glue.job_run.distribution` por capacidade e estado terminal, e `glue.job_run.outcome` por capacidade. DPU e observado quando a API o traz, derivado quando a capacidade e estatica, e recusado sob Auto Scaling sem DPUSeconds. Com `cloudwatch`, correlaciona por job_run_id; sem ele, a correlacao vai para unresolved com o comando que a resolve.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `job_name` | string | sim |  |
| `path` | string | sim | DIRETORIO de artefatos gravados por `collect glue-job-runs`. |
| `cloudwatch` | string | não | Diretorio de artefatos gravados por `collect cloudwatch`. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze cloudwatch`](../cli/analyze.md), [`sparkforge analyze event-log`](../cli/analyze.md), [`sparkforge analyze glue-job-runs`](../cli/analyze.md), [`sparkforge analyze sql-metrics`](../cli/analyze.md)

## Capacidade

extract facts from a Spark event log

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
