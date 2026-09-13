<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_code_status`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

O estado do indice local e NENHUM fonte: se existe, se esta fresco em relacao a arvore, contagem de arquivos/simbolos/arestas/nao-resolvidas, versao de schema, worktree e tamanho do banco. E a UNICA consulta que nao recusa com indice velho ou ausente -- ela responde SOBRE o grafo, nao COM o grafo, e recusar deixaria o operador sem o verbo que explica por que as outras recusaram. Nunca escreve no indice. Em `detail_level: full` acrescenta o bloco de seguranca e o de mudancas -- quais simbolos moram nos arquivos alterados e quem os chama --, sem gerar commit nem alterar Git.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio analisado. Nada e lido fora dela. |
| `db` | string | não | Arquivo do indice. Omitido, o default e `.sparkforge/local/codeintel/graph.sqlite3` sob `repo`. |
| `detail_level` | string: `summary`, `normal`, `full` | não |  |

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
