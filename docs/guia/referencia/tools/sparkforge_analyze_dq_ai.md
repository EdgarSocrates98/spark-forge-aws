<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_dq_ai`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de um manifesto externo de recomendacao Glue DQ BASIC ou ADVANCED. Le somente metadata, rejeita campos que carreguem rows e nao chama Bedrock, Glue ou Athena.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim |  |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge-aws analyze dq-ai`](../cli/analyze.md), [`sparkforge-aws dq-ai assess`](../cli/dq-ai.md)

## Capacidade

compose deterministic data-quality AI assessment

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
