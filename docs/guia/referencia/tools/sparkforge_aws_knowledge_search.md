<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_knowledge_search`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Knowledge Search: busca textual deterministica e offline sobre os `.md`/`.yaml` da raiz resolvida e dos packs ativos — casa o termo sem case em nome e conteudo. Devolve `documents` — uma entrada por documento (path, dominio, sha256, `line_hits` e as primeiras linhas que casam, enderecados `packs/<id>/<rel>`) — `documents_total`, `matched` (so os paths), `knowledge_root`/`knowledge_origin` e `next_cursor` para paginar por documento; `truncated` marca o corte. `domain` restringe ao primeiro segmento do caminho. O QUE ELA NAO FAZ: nao ranqueia, nao interpreta, nao acessa rede.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `term` | string | sim | Termo buscado (sem case). |
| `cursor` | string | não | Cursor da paginacao por documento (`next_cursor` da pagina anterior). |
| `domain` | string | não | Restringe a documentos cujo primeiro segmento de caminho (ou nome de arquivo na raiz) leva o prefixo do dominio. |
| `limit` | integer | não | Teto de documentos por pagina (default 20). |

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
