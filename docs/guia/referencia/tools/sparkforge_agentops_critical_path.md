<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_agentops_critical_path`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Caminho critico medido do run (duracao observada, nao o DAG do metodo CPM): maiores duracoes, retries e waiting entre spans consecutivos.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
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
| `readOnlyHint` | `true` |
