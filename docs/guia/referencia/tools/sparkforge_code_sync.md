<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_code_sync`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

A UNICA tool de mutacao do Code Intelligence: poe o indice local em dia com a arvore. Escreve somente em `.sparkforge/local/codeintel/**` e nunca toca o fonte do repositorio analisado. Cai para reconstrucao completa quando o banco esta ausente, vazio ou e de outra raiz, e diz qual dos dois aconteceu em `full_rebuild`. Chame quando outra tool recusar com `STALE_INDEX` ou `INDEX_MISSING`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio analisado. Nada e lido fora dela. |
| `db` | string | não | Arquivo do indice. Omitido, o default e `.sparkforge/local/codeintel/graph.sqlite3` sob `repo`. |

## Na CLI

[`sparkforge code status`](../cli/code.md), [`sparkforge code sync`](../cli/code.md)

## Capacidade

conferir e sincronizar o frescor do indice de codigo

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
