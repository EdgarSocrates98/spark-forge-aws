<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_context_start`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Context Gateway deterministico: descobre capabilities relevantes, seleciona contexto local, reduz por ordem fixa e devolve refs ctx://v1 expansíveis. Nao chama provider, nao le artefato arbitrario e exige max_bytes explicito.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `intent` | string | sim |  |
| `max_bytes` | integer | sim |  |
| `profile` | string: `economy`, `balanced`, `deep` | sim |  |
| `case_id` | string | não |  |
| `items` | array de object | não |  |
| `repo` | string | não |  |

## Na CLI

[`sparkforge context expand`](../cli/context.md), [`sparkforge context start`](../cli/context.md)

## Capacidade

discover and expand selective context under a hard byte budget

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
