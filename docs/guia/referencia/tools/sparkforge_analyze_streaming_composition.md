<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_streaming_composition`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Compõe facts já extraídos de Structured Streaming, transporte e Iceberg. Exige identidade declarada (`table`/`query_name` ou `transport_key`) e só produz link quando a correspondência é observada sem ambiguidade. Preserva ids dos facts de origem, operações Iceberg, lag/iterator age, avaliação SLO de progress/sink/Kafka/Kinesis, janela temporal pareada e unresolved. `streaming_sink` liga num_output_rows ao batch por batch_id; `sink_name` pode desambiguar descrições. Modes temporal e iceberg_temporal exigem `max_skew_seconds` declarado. Não consulta AWS, Kafka, Spark ou Iceberg e não infere causalidade.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_paths` | array de string | sim | Arquivos de facts produzidos por analyzers; repetível. |
| `mode` | string: `iceberg`, `iceberg_temporal`, `observability`, `slo`, `temporal` | sim | Relação streaming→Iceberg, janela streaming→Iceberg, progresso→transporte, SLO→progress/sink/transporte ou janela temporal pareada. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |
| `max_skew_seconds` | number | não | Tolerância temporal declarada para modes temporal/iceberg_temporal; sem valor sai unresolved. |
| `query_name` | string | não | Query Structured Streaming declarada. |
| `slo_name` | string | não | Nome do SLO declarado; obrigatório quando há mais de uma declaração. |
| `table` | string | não | Tabela Iceberg declarada. |
| `transport_key` | string | não | Grupo/topic Kafka ou stream Kinesis declarado. |

## Na CLI

[`sparkforge analyze streaming-composition`](../cli/analyze.md)

## Capacidade

compose streaming lakehouse and transport observability evidence

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
