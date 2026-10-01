<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_decision_evaluate`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Avalia contrato de decisão bounded, versionado e local através do kernel determinístico. Não chama provider, não acessa AWS e não altera o router. Preserva ACCEPTED, ABSTAIN, UNRESOLVED e REFUSED, fingerprint, receipt verificável e medição local; provider_tokens permanece unresolved sem transcript do host.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `contract` | string | sim |  |
| `repo` | string | sim |  |
| `state` | object | sim |  |
| `now` | string | não |  |

## Na CLI

[`sparkforge decision evaluate`](../cli/decision.md)

## Capacidade

evaluate a bounded deterministic decision offline

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
