<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_analyze_data_observability`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Avalia SLI/SLO, freshness, completeness, latency, lag, throughput e availability a partir de medições exportadas. Calcula compliance e error budget, preserva incidentes/MTTR, dependências e blast radius declarado. Não consulta Prometheus, CloudWatch ou OTel live; ausência de medição vira unresolved.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo JSON/YAML de observabilidade. |

## Na CLI

[`sparkforge-aws analyze data-observability`](../cli/analyze.md)

## Capacidade

evaluate offline data observability and SRE SLO evidence

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
