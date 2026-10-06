<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_orchestration`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Normaliza um inventário de Airflow, Dagster, Step Functions e Control-M com schedules, sensors, retries, backoff, pools, concurrency, backfill, idempotência e dependências. Não dispara workflow nem executa backfill; propriedade ausente ou referência inválida permanece unresolved.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo JSON/YAML do control plane. |

## Na CLI

[`sparkforge-aws analyze orchestration`](../cli/analyze.md)

## Capacidade

normalize orchestration control plane across Airflow Dagster Step Functions and Control-M

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
