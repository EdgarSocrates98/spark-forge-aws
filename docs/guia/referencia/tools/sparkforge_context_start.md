<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_context_start`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Context Gateway deterministico: descobre capabilities relevantes, seleciona contexto local, reduz por ordem fixa e devolve refs ctx://v1 expansíveis. Nao chama provider nem le artefato arbitrario; max_bytes usa default do perfil quando omitido.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `intent` | string | sim |  |
| `profile` | string: `economy`, `balanced`, `deep` | sim |  |
| `answer_reasons` | array de string | não |  |
| `answer_status` | string: `resolved`, `partial`, `unavailable` | não |  |
| `case_id` | string | não |  |
| `items` | array de object | não |  |
| `max_bytes` | integer | não |  |
| `repo` | string | não |  |
| `role` | string | não | Role com plano declarado em ROLE_PLANS (sf-inventory, sf-extractor, sf-judge, sf-verifier, sf-synthesizer). Role desconhecida nega contexto (fail-closed). |
| `role_plan` | object | não | RoleContextPlan serializado (to_dict). Vence `role`. Invalido nega contexto com unresolved role_plan_invalid. |
| `triggers` | array de string | não |  |

## Na CLI

[`sparkforge-aws context expand`](../cli/context.md), [`sparkforge-aws context start`](../cli/context.md)

## Capacidade

discover and expand selective context under a hard byte budget

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
