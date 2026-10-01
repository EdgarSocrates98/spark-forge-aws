<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_code_search`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Busca simbolo por parte do nome no indice local e devolve `node_id`, caminho e linha -- o suficiente para ir ao codigo sem que o indice guarde codigo. O termo NUNCA vira consulta bruta: ele e tokenizado e escapado antes do FTS, entao operador digitado pelo chamador vale como texto literal. Nenhum regex e nenhum SQL sao aceitos. Lista vazia significa 'nenhum simbolo casou', e o indice foi conferido contra a arvore antes de responder -- nunca e uma ausencia por indice velho.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `query` | string | sim |  |
| `repo` | string | sim | Raiz do repositorio analisado. Nada e lido fora dela. |
| `db` | string | não | Arquivo do indice. Omitido, o default e `.sparkforge/local/codeintel/graph.sqlite3` sob `repo`. |
| `kind` | string | não | Filtra por tipo de no (`function`, `class`, `method`, ...). |
| `limit` | integer | não |  |
| `path_prefix` | string | não | Filtra por prefixo do caminho relativo, ex.: `jobs/`. |

## Na CLI

[`sparkforge code search`](../cli/code.md)

## Capacidade

localizar simbolo no indice local de codigo

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
