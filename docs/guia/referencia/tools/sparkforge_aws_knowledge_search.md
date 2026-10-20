<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_knowledge_search`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Knowledge Search: busca textual deterministica e offline sobre os `.md`/`.yaml` da raiz resolvida e dos packs ativos — casa o termo sem case em nome e conteudo. Devolve `matched` (docs com hit, enderecados `packs/<id>/<rel>`), `matched_total` e as primeiras `limit` ocorrencias `{file, line, text}` — nunca o arquivo inteiro; `truncated` marca o corte. O QUE ELA NAO FAZ: nao ranqueia, nao interpreta, nao acessa rede.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `term` | string | sim | Termo buscado (sem case). |
| `limit` | integer | não | Teto de ocorrencias devolvidas (default 20). |

## Na CLI

[`sparkforge-aws knowledge list`](../cli/knowledge.md), [`sparkforge-aws knowledge search`](../cli/knowledge.md)

## Capacidade

inventory and search the knowledge corpus offline

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
