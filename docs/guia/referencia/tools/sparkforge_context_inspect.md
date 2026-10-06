<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_context_inspect`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Inspeciona qualidade de contexto fornecido pelo chamador. Mede bytes, relevancia, duplicacao, frescor e cobertura de evidencia; nunca converte bytes em tokens. Tokens do provider so entram quando transcript os mediu.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `payload` | object | sim |  |
| `observed_provider_tokens` | integer ou null | não |  |

## Na CLI

[`sparkforge-aws agentops baseline`](../cli/agentops.md), [`sparkforge-aws agentops compare`](../cli/agentops.md), [`sparkforge-aws agentops critical-path`](../cli/agentops.md), [`sparkforge-aws agentops inspect`](../cli/agentops.md), [`sparkforge-aws agentops timeline`](../cli/agentops.md), [`sparkforge-aws context inspect`](../cli/context.md), [`sparkforge-aws doctor agentic`](../cli/doctor.md)

## Capacidade

inspect agentic context quality and local AgentOps economy

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
