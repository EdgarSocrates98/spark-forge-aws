<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_terraform_diff`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Compara dois estados de um modulo Terraform (dois checkouts, dois `git worktree`, o main e o branch do PR) e devolve os facts do lado DEPOIS, com `attrs.changed` e `attrs.previous_value` no que mudou. Nao roda terraform: le o HCL, que e o que o revisor do PR ve. Desbloqueia SF-GLUE-005, que pergunta se alguem aumentou o worker sem evidencia de pressao de memoria -- e por isso exige tambem o event log do run.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `after` | string | sim | Diretorio do estado proposto. |
| `before` | string | sim | Diretorio do estado anterior. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze terraform-diff`](../cli/analyze.md)

## Capacidade

compare two Terraform states and mark what changed

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
