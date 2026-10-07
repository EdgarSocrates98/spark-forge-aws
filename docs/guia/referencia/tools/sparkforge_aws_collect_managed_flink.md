<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_collect_managed_flink`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Coleta a descrição de uma aplicação do Managed Service for Apache Flink via kinesisanalyticsv2.DescribeApplication, sempre com IncludeAdditionalDetails=false. Registra runtime, status, versão, checkpoint, paralelismo, VPC, logging e configuração observados; com janela explícita, consulta cinco métricas de aplicação em AWS/KinesisAnalytics. Job plan, código e conectores ficam unresolved e nunca são inferidos. Somente leitura AWS; grava apenas artifact/manifesto local e usa cache offline-first.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `application_name` | string | sim |  |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `metrics_end` | string | não | Fim ISO 8601 da janela CloudWatch. |
| `metrics_period` | integer | não |  |
| `metrics_start` | string | não | Início ISO 8601 da janela CloudWatch. |
| `region_name` | string | não |  |

## Na CLI

[`sparkforge-aws collect managed-flink`](../cli/collect.md)

## Capacidade

collect Managed Flink configuration and bounded temporal metrics read-only

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `true` |
| `readOnlyHint` | `false` |
