<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_agentops_compare`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Compara dois runs AgentOps locais sem atribuir causa ou converter bytes em tokens.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `run_a` | string | sim |  |
| `run_b` | string | sim |  |
| `db_path` | string | não |  |
| `repo` | string | não |  |

## Na CLI

[`sparkforge agentops baseline`](../cli/agentops.md), [`sparkforge agentops compare`](../cli/agentops.md), [`sparkforge agentops inspect`](../cli/agentops.md), [`sparkforge context inspect`](../cli/context.md), [`sparkforge doctor agentic`](../cli/doctor.md)

## Capacidade

inspect agentic context quality and local AgentOps economy

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
