<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_sdd_status`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Fase atual de cada feature do SDD, o status declarado, a proxima fase e os codigos de recusa e lacuna que a impedem de avancar. Mesmos gates de `sparkforge_sdd_check`, na mesma varredura, agrupados por feature; a lacuna sem feature (raiz ausente, arquivo pulado na raiz) sai em `unresolved`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio. |
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
