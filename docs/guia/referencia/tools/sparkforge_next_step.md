<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_next_step`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Decide o proximo passo (skill recomendada) a partir de routing.yaml -- o mesmo motor declarativo de sparkforge.rules.engine, mas sobre o estado do case e os achados atuais, nunca sobre o julgamento livre do agente. `blocked_by` e advisory: informa gates pendentes sem impedir a chamada.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim |  |
| `findings` | array de object | não | Findings atuais, usados para casar condicoes de roteamento. |

## Na CLI

[`sparkforge next-step`](../cli/next-step.md)

## Capacidade

route the next step deterministically

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
