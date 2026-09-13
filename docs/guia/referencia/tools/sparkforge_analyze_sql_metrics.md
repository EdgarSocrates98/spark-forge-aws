<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_sql_metrics`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai metrica por NO DO PLANO de um Spark event log ja coletado: quantos bytes e quantos arquivos cada fonte custou, medidos pelo proprio Spark. Responde o que `analyze event-log` nao responde -- aquele mede por stage, e stage agrega todas as leituras que caem nele. Metrica que a execucao nao publicou fica AUSENTE, nunca zero; nome de metrica fora do mapa canonico vira `spark.sql.unresolved` com o nome cru, nunca palpite.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo de event log (.jsonl). |
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
