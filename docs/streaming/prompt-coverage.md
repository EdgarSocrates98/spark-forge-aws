# Cobertura auditada de `prompt_evo_streaming.md`

Data da auditoria: 2026-10-02. Esta matriz foi escrita depois de executar
`sparkforge sdd status`, `sparkforge sdd check` nas features de streaming e
`sparkforge code sync`; ela mede artefatos existentes, não menções em Markdown.

## Estado atual antes da conclusão do prompt

| Capability | Nível medido | Evidência atual | Lacuna para P0/P1 |
|---|---|---|---|
| Structured Streaming | `diagnosable` parcial | `sparkforge/facts/pyspark_ast.py`, `facts/streaming.py`, `rules/catalog/streaming.yaml`, `sparkforge_analyze_streaming` | checkpoint metadata interno, versões Spark/Glue, joins/state/checkpoint cross-artifact e skill dedicada |
| Spark Real-Time | `knowledge-only` | knowledge geral Spark/streaming | matriz de versão e separação upstream/runtime gerenciado |
| Kafka | `fact-aware` parcial | `facts/transport.py`, `fixtures/transport`, `sparkforge_analyze_transport` | Connect, Streams, collectors, métricas temporais, rules e segurança completa |
| Amazon MSK | `fact-aware` parcial | `msk.cluster` em `facts/transport.py`, `knowledge/transport-diagnostics.md` | matriz upstream↔MSK↔broker, configuração/rede/segurança/lag e collector read-only |
| Kafka Connect | `knowledge-only` | nenhuma família de facts/rules própria | config/status/tasks/offsets/DLQ e comparação arquitetural |
| Kafka Streams | `knowledge-only` | sem extractor/rules próprios | state stores, repartition, joins/windows e decisão contra Spark/Flink |
| Kinesis Data Streams | `fact-aware` parcial | `kinesis.stream/shard/metric` e goldens | collector/CloudWatch temporal, reshard, KCL/EFO e rules com evidência |
| Apache Flink | `knowledge-only` | sem facts, analyzer ou rules próprios | config, state, checkpoints, savepoints, backpressure, runtime matrix |
| Managed Service for Apache Flink | `knowledge-only` | sem artefato ou matriz própria | separar upstream/AWS, application config, connectors, IAM/VPC/CloudWatch |
| Glue Streaming | `workflow-only` parcial | conhecimento Glue e AST streaming | job/Terraform cross-artifact, runtime guards, source/sink e rules |
| Glue Real-Time Mode | `knowledge-only` | referências dispersas no prompt/knowledge Glue | capability versionada, restrições Glue 6.x revalidadas e rules |
| CDC | `knowledge-only` | sem domínio CDC próprio | snapshot/CDC/transaction/delete/replay/DDL facts e troubleshooting |
| AWS DMS | `knowledge-only` | nenhum analyzer DMS | task/endpoint/mapping/stats/logs e recovery sem collector write-capable |
| Debezium | `knowledge-only` | nenhum analyzer Debezium | connector config, snapshot, heartbeat, tombstone, outbox e schema history |
| Schema Registry/data contracts | `knowledge-only` | `knowledge/data-contracts-schema-evolution.md` | registry/schema-version/diff determinístico, oito compatibilities, integrations |
| Streaming + Iceberg | `workflow-only` parcial | `facts/iceberg_metadata.py`, regras Iceberg e facts streaming separados | correlação progress↔snapshots/commits/files/metadata e evidence-driven rules |
| Delta/Hudi | `knowledge-only` | conhecimento Iceberg dominante | matrizes de compatibilidade e decisão arquitetural; collectors ficam P1/P2 |
| Event-driven architecture | `knowledge-only` | skills AWS messaging e workflows genéricos | artifact contract para EventBridge/Pipes/SQS/SNS/Step Functions e decisão vs streaming |
| Streaming observability | `artifact-aware` parcial | progress facts e Glue observability | lag/backpressure/freshness/SLO/lineage/telemetry cross-service |
| Streaming FinOps | `knowledge-only` | FinOps batch/genérico | custo por transport/process/runtime/sink e evidence path temporal |
| Streaming security | `knowledge-only` | skills AWS IAM/security genéricas | facts de TLS/IAM/KMS/VPC/secrets/cross-account e revisão de collectors |
| Real-time analytics/serving | `knowledge-only` | nenhuma família real-time própria | Redshift streaming, Delta/Hudi e knowledge P1; ClickHouse/Pinot/Druid/Trino P2 |
| Architecture decision support | `workflow-only` parcial | `design-data-architecture`, `decision` e matriz genérica | facts declarados, eliminação por constraint, ADR streaming e evidence/cost unresolved |

## O que já foi realmente entregue

- Wave B: Structured Streaming source/progress facts, três rules, CLI/MCP,
  fixtures e knowledge.
- Wave C parcial: dumps offline Kafka/MSK/Kinesis, facts específicos,
  unresolved, fixtures, CLI/MCP e locks.
- SDD fechado para essas duas waves: `STREAMING_REALTIME_DATA_PLATFORM` e
  `STREAMING_TRANSPORT_DIAGNOSTICS`.

## Waves necessárias para fechar o prompt

| Wave | Escopo | Critério de fechamento |
|---|---|---|
| D | Flink + Managed Flink | artifact contract, extractor, unresolved, version matrix, rules, fixtures, analyzer e skill |
| E | Glue Streaming + RTM | job/Terraform cross-artifact, runtime guard, capability evidence e rules |
| F | CDC + Debezium + DMS + Schema | config analyzers, contract diff, compatibility, transactions, fixtures e routing |
| G | Iceberg streaming + observability + lineage + SLO + FinOps | correlação temporal, não inferência causal, telemetry/context drill-down |
| H | Event-driven + architecture decision + agents/skills/routing | requirements→facts→candidates→constraints→ADR com unresolved |
| I | Delta/Hudi/Redshift and P2 knowledge | matrices/evals e artefacts somente onde existir caminho determinístico |
| J | security, failure fixtures, integration, performance, packaging and all gates | full suite, package/install/CLI/MCP smoke, security/economy review |

## Regra de conclusão

O prompt só pode ser marcado fechado quando cada domínio P0 tiver o checklist
da seção 50 com `N/A + motivo` onde aplicável, cada wave tiver SDD `ship` verde
e o relatório final separar capacidade comprovada de `unresolved`. Esta matriz
continua deliberadamente aberta até essas evidências existirem.
