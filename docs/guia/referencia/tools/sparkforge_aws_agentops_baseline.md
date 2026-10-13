<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_agentops_baseline`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Salva ou compara baseline AgentOps em arquivo local content-addressed por run declarado.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `action` | string: `save`, `compare` | sim |  |
| `baseline_path` | string | sim |  |
| `run_id` | string | sim |  |
| `db_path` | string | não |  |
| `repo` | string | não |  |

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
| `readOnlyHint` | `false` |
