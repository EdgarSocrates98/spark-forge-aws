<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_sdd_stamp`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Grava `upstream.sha256` no frontmatter de um artefato SDD, com o hash de texto do upstream declarado. Muda so a linha do hash, preserva quebra de linha, BOM e corpo, e nao regrava quando o hash ja confere. So escreve em <root_path>/<FEATURE>/<fase>.md; linha de hash que ele nao sabe reescrever e recusada por nome. Use depois de revisar uma fase cujo upstream mudou (`upstream_stale`).

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Artefato, relativo a `repo`. |
| `repo` | string | sim | Raiz do repositorio. |
| `root_path` | string | não | Pasta dos artefatos relativa a `repo` (padrao docs/sdd). |

## Na CLI

[`sparkforge sdd stamp`](../cli/sdd.md)

## Capacidade

record the upstream hash of a spec artifact

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
