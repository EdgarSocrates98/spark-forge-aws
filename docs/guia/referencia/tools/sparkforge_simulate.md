<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_simulate`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Simulate: o que uma mudanca de configuracao move, ESTRUTURALMENTE. Cada item de `sets` e `camada:chave=valor`, com a camada obrigatoria -- `tf` (tf.spark_conf, tf.attribute), `code` (pyspark.conf_set), `effective` (spark.conf_effective) ou `emr` (emr/emrs/emrc.configuration). O valor troca em TODO fact da camada que declara a chave, e so nesses: chave que a camada nao declara e recusada (`chave_ausente_na_camada`), assim como texto para uma medida numerica. Os dois lados passam pelo mesmo pipeline -- tirar os derivados, rederivar (fusion, Lake Formation, timeout), detectar o runtime e julgar -- e a comparacao, pela chave estavel do subject, devolve `disappeared`, `appeared`, `persisted_count` e `skipped_delta`. O QUE ELA NAO FAZ, e isto e contrato: nunca preve spill, tempo ou custo (nao sao fact de configuracao), nao julga compatibilidade de dependencia (use `sparkforge_migration_assess`) e nao preve o grafo de execucao. As tres recusas saem em `refused`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string ou array de string | sim | Facts do case, gerados por `sparkforge analyze * --out`. |
| `sets` | array de string | sim | camada:chave=valor, por exemplo tf:max_concurrent_runs=1. |
| `athena` | string | não |  |
| `emr` | string | não |  |
| `glue` | string | não |  |
| `iceberg` | string | não |  |
| `python` | string | não |  |
| `spark` | string | não |  |

## Na CLI

[`sparkforge simulate`](../cli/simulate.md)

## Capacidade

show what a configuration change would structurally move

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
