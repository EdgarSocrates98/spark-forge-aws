<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_sdd_check`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Confere os artefatos de spec do SDD proprio (docs/sdd/<FEATURE>/<fase>.md: explore, define, design, plan, build_report, ship). Julga so o frontmatter: schema, ordem das fases, hash do upstream (cascata), cobertura dos acceptance tests, teste por task (TDD), rollback, red declarado, evidencia de afirmacao, hipotese fechada, registros exigidos pelo tipo de mudanca e, no perfil operator, case e sandbox existentes. Cada falha sai em `refused` com `code` e `unlock`; o que ele nao consegue decidir (raiz ausente, caminho que a varredura pulou) sai em `unresolved`. NAO julga a prosa e nao chama modelo.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio. |
| `feature` | string | não | Confere so esta feature. Feature que nao existe e erro, salvo quando uma lacuna ja explica a ausencia. |
| `root_path` | string | não | Pasta dos artefatos relativa a `repo` (padrao docs/sdd). |

## Na CLI

[`sparkforge sdd check`](../cli/sdd.md), [`sparkforge sdd status`](../cli/sdd.md)

## Capacidade

check spec artifacts against the SDD contract

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
