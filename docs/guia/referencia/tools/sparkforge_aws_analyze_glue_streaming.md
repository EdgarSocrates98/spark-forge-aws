<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_analyze_glue_streaming`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts determinísticos de dumps JSON/JSONL já salvos de AWS Glue Streaming e Real-Time Mode. Preserva runtime, modo, fonte, restrições observadas, capacidade e unresolved quando a medida faltar. Não chama Glue, Kafka, Kinesis ou CloudWatch.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo ou diretório JSON/JSONL. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge-aws analyze glue-streaming`](../cli/analyze.md)

## Capacidade

extract AWS Glue Streaming and Real-Time Mode artifact facts

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
