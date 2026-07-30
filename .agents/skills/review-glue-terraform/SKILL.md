---
name: review-glue-terraform
description: Use quando revisar o Terraform/IaC de jobs Glue (worker type, número de workers, Auto Scaling, execution class, timeout, retries, default arguments, Spark UI/event logs, catálogo Iceberg, IAM, bookmarks) em busca de configs de performance/observabilidade ausentes, contraditórias ou incompatíveis com o runtime.
---

# Review Glue Terraform

## Recursos e parâmetros

Avalie:
- Glue version;
- worker type;
- number of workers;
- max capacity;
- Auto Scaling;
- execution class;
- timeout;
- retries;
- max concurrent runs;
- job run queuing;
- default arguments;
- non-overridable arguments;
- Spark UI;
- event logs S3;
- continuous logs;
- observability metrics;
- temp directory;
- extra Python files/modules;
- extra JARs;
- classpath precedence;
- Data Catalog;
- Iceberg catalog configuration;
- Lake Formation;
- IAM;
- VPC/subnets/security groups;
- KMS;
- bookmarks;
- job language/runtime.

## Regras

- Relacionar cada ajuste à evidência operacional.
- Não sugerir workers sem baseline de CPU, heap, spill e tasks.
- Confirmar compatibilidade Glue/Spark/Iceberg.
- Alertar sobre argumentos contraditórios.
- Verificar se configs definidas no código sobrescrevem Terraform.
- Verificar observabilidade suficiente para diagnosticar produção.
- Não expor segredos.

## Saída

- inventário Terraform;
- riscos;
- divergências;
- configurações ausentes;
- patch sugerido;
- impacto esperado como hipótese;
- plano de rollout/rollback.

## Quando NÃO usar

- Você quer decidir o tamanho/perfil de worker a partir de métricas: use `tune-glue-job`.
- O problema está no código ou nos dados, não na config: comece pelo diagnóstico.
- Revisão de código de aplicação PySpark: use `review-pyspark-pr`.

## Referência rápida

| Config no IaC | O que checar | Risco se errado |
|---|---|---|
| `--enable-spark-ui` / event logs S3 | habilitado e com destino válido | sem observabilidade para diagnosticar produção |
| Auto Scaling + number of workers | teto coerente com curva de executors | superprovisão (custo) ou subprovisão |
| default arguments Spark/Iceberg | compatíveis com a Glue version | falha de runtime; config ignorada |
| args definidos também no código | precedência código × Terraform | Terraform sobrescrito silenciosamente |
| `max concurrent runs` / queuing | coerente com SLA e concorrência real | contenção ou fila indevida |
| bookmarks | usados corretamente (não como incremental universal) | reprocessamento ou perda de dados |

## Red flags

- Sugerir mais workers sem baseline de CPU/heap/spill/tasks.
- Copiar configs entre versões de Glue sem checar `knowledge/runtime-compatibility.md`.
- Expor segredos em default arguments ou logs.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
