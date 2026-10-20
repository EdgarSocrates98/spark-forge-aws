<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_knowledge_list`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Knowledge List: enumera os documentos de knowledge versionado (e dos packs ativos em `packs/<id>/<rel>`) sobre a mesma raiz resolvida por `knowledge_path` — env override, workspace, checkout com marcador ou o bundle do wheel. Resposta fina: `root` + `docs` (paths relativos). O QUE ELA NAO FAZ: nao le conteudo (isso e `knowledge_search`/`code_read`), nao atualiza a raiz e nao acessa rede.

## Parâmetros

Esta tool não recebe parâmetros.

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
