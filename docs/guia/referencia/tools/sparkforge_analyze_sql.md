<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_sql`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de texto SQL por regex/varredura de token (nunca uma gramatica SQL completa): projecao (`SELECT *` vs. colunas explicitas), predicados de WHERE, uso de LIMIT. Dois modos, mutuamente exclusivos: `path` le um arquivo .sql; `from_pyspark` varre um arquivo .py via AST e extrai o literal de cada chamada `spark.sql("...")` (argumento nao-literal vira `sql.unresolved` com reason `non_literal_sql`, nunca uma referencia seguida). NAO sabe se uma coluna e de particao nem seu tipo declarado -- isso exige `sparkforge_fuse` correlacionando com `sparkforge_analyze_catalog_schema`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `from_pyspark` | string | não | Arquivo .py: extrai texto de chamadas spark.sql("...") em vez de ler `path`. Mutuamente exclusivo com `path`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |
| `path` | string | não | Arquivo .sql a analisar. |

## Na CLI

[`sparkforge analyze sql`](../cli/analyze.md)

## Capacidade

extract facts from SQL text and spark.sql literals

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
