<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_forge_lab`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Descreve a topologia declarativa do Forge Lab/Digital Twin, incluindo Kafka, Flink, Spark, Iceberg REST, Polaris, MinIO, PostgreSQL, Debezium e Prometheus, ordem de dependências e cenários de falha. É offline e read-only: não executa Docker, não mata broker, não reinicia CDC e não muta dados. Cenários exigem confirmação do operador fora desta tool.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo JSON ou YAML da topologia Forge Lab. |

## Na CLI

[`sparkforge analyze forge-lab`](../cli/analyze.md)

## Capacidade

describe offline Forge Lab topology and failure scenarios

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
