<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_call_graph`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts JA extraidos (tipicamente `sparkforge_analyze_pyspark` gravado em disco via `--out`) -- funcao pura sobre Facts, nunca reparseia codigo-fonte. Revela trabalho Spark (`count()`, `write`, `collect`) escondido dentro de um helper chamado varios niveis abaixo do entrypoint, invisivel numa revisao que so olha o entrypoint. Sem `unresolved` proprio: so deriva do que ja foi resolvido.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string | sim | Arquivo de facts gerado por `sparkforge_analyze_pyspark`. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze call-graph`](../cli/analyze.md)

## Capacidade

derive a call graph and Spark work reachability from facts

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
