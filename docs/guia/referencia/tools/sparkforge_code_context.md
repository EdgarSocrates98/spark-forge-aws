<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_code_context`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

A tool PRINCIPAL do Code Intelligence: monta o ContextPack de uma tarefa a partir do indice local do repositorio -- pontos de entrada, simbolos ranqueados, relacoes do grafo, referencias nao resolvidas e os ids de regra relevantes ao vocabulario da consulta -- tudo dentro de um orcamento de tokens. Substitui varrer o repositorio arquivo a arquivo. O texto de `task` NAO volta na resposta: o que volta e a expansao dele pelo dicionario versionado. `lineage` sai do indice, com o que nao se sabe nomear marcado como recusa em vez de adivinhado; `snippets` sai SEMPRE vazio -- trecho de fonte sai por `sparkforge_code_read`. Recusa em vez de responder quando o indice esta atras da arvore.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio analisado. Nada e lido fora dela. |
| `task` | string | sim | A pergunta em linguagem natural. Nunca ecoada de volta. |
| `db` | string | não | Arquivo do indice. Omitido, o default e `.sparkforge/local/codeintel/graph.sqlite3` sob `repo`. |
| `include` | array de string | não | Secoes a preencher. `snippets` e RECUSADO com a razao em vez de devolvido vazio. Em `lineage` a recusa desceu de nivel: a secao responde, e o ITEM que nao se pode nomear sai marcado. |
| `max_tokens` | integer | não | Teto do pacote. Fora da faixa satura no limite, nao recusa. |

## Na CLI

[`sparkforge code context`](../cli/code.md)

## Capacidade

montar contexto de codigo dentro de um orcamento de tokens

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
