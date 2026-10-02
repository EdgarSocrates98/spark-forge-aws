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
| Apache Flink | `diagnosable` parcial | `facts/flink.py`, `rules/catalog/flink.yaml`, `sparkforge_analyze_flink`, fixtures e `analyze-flink-job` | collector/matriz de runtime, savepoints, métricas temporais e validação funcional |
| Managed Service for Apache Flink | `diagnosable` parcial | namespace `managed_flink.*`, config/connectors/metrics, unresolved, fixtures e mesmo analyzer | collector/matriz upstream↔AWS, IAM/VPC/CloudWatch temporal e validação funcional |
| Glue Streaming | `diagnosable` parcial | `facts/glue_streaming.py`, regras RTM, fixtures, CLI/MCP e `review-glue-streaming` | job/Terraform cross-artifact, runtime matrix/collector, source/sink e validação funcional |
| Glue Real-Time Mode | `diagnosable` parcial | namespace `glue.streaming.*`, restrições/capacidade observadas, rules e unresolved | matriz completa, collector live, cross-artifact e validação funcional |
| CDC | `diagnosable` parcial | `facts/cdc.py`, regras `SF-CDC`, fixtures de evento/connector/seam/unresolved, CLI/MCP e `review-cdc-replication` | collector/replay temporal, cross-artifact com consumidor e validação funcional |
| AWS DMS | `diagnosable` parcial | namespace `dms.*`, task/endpoint/mapping/stats/unresolved, rules e fixtures | collector read-only, matriz de versões, logs temporais e recovery funcional |
| Debezium | `diagnosable` parcial | namespace `debezium.*`, config/status/schema-history/tombstone/unresolved, rules e fixtures | collector Kafka Connect, matriz de versões, offsets/DLQ e replay funcional |
| Schema Registry/data contracts | `diagnosable` parcial | `facts/schema_registry.py`, `rules/catalog/schema_registry.yaml`, fixtures `schema_registry`, `sparkforge_analyze_schema_registry`, `review-cdc-replication` | collectors/live registry, matriz completa de formato/versão, consumidores cross-artifact e validação funcional |
| Streaming + Iceberg | `diagnosable` parcial | `facts/iceberg_metadata.py`, `facts/streaming_composition.py`, `analyze streaming-composition`, regras `streaming_composition.yaml` e goldens | collectors/live lineage, SLO/FinOps e validação causal/funcional permanecem lacunas |
| Delta/Hudi | `knowledge-only` | conhecimento Iceberg dominante | matrizes de compatibilidade e decisão arquitetural; collectors ficam P1/P2 |
| Event-driven architecture | `diagnosable` parcial | `facts/event_driven.py`, regras `SF-EVENT`, fixtures, `analyze event-driven`, MCP, skill, routing e SDD | collector live, Step Functions, teste temporal de entrega/replay e decisão vs streaming |
| Streaming observability | `diagnosable` parcial | progress/transport facts, `facts/streaming_composition.py`, `analyze streaming-composition` e regras offline de lag/iterator age | collectors temporais, SLO, lineage cross-service e FinOps permanecem lacunas |
| Streaming FinOps | `knowledge-only` | FinOps batch/genérico | custo por transport/process/runtime/sink e evidence path temporal |
| Streaming security | `knowledge-only` | skills AWS IAM/security genéricas | facts de TLS/IAM/KMS/VPC/secrets/cross-account e revisão de collectors |
| Real-time analytics/serving | `knowledge-only` | nenhuma família real-time própria | Redshift streaming, Delta/Hudi e knowledge P1; ClickHouse/Pinot/Druid/Trino P2 |
| Architecture decision support | `diagnosable` parcial | `sparkforge architecture streaming`, matriz de candidatos, fixtures, skill e ADR offline | integração com facts de runtime/serving, custo/SLO/security observados e validação experimental |

## O que já foi realmente entregue

- Wave B: Structured Streaming source/progress facts, três rules, CLI/MCP,
  fixtures e knowledge.
- Wave C parcial: dumps offline Kafka/MSK/Kinesis, facts específicos,
  unresolved, fixtures, CLI/MCP e locks.
- Wave D: dumps offline Flink/Managed Flink, namespaces separados, regras de
  checkpoint/backpressure, unresolved, fixtures, CLI/MCP, skill, especialista,
  routing e SDD ship.
- Wave F parcial: Schema Registry/data contracts com registro, definição,
  compatibilidade declarada, diff estrutural, auto-register, unresolved,
  fixtures, CLI/MCP, skill, routing e SDD ship.
- Wave G parcial: composição offline entre streaming, Iceberg e observabilidade
  de Kafka/Kinesis, com identidade declarada, facts linkados, unresolved,
  rules evidence-driven, CLI/MCP, skill, routing, fixtures e SDD.
- Wave H parcial: contrato offline de EventBridge rules/Pipes, SQS e SNS, com
  DLQ/redrive/target facts, unresolved, rules evidence-driven, CLI/MCP, skill,
  routing, fixtures, mirrors, bundle offline e SDD ship.
- SDD fechado para essas waves: `STREAMING_REALTIME_DATA_PLATFORM`,
  `STREAMING_TRANSPORT_DIAGNOSTICS`. Wave D: `STREAMING_FLINK_PLATFORM`.
- Wave H2: decisão offline separa requirements de assumptions, elimina por
  constraints factuais e mantém ADR unresolved quando há empate ou blind spot.

## Waves necessárias para fechar o prompt

| Wave | Escopo | Critério de fechamento |
|---|---|---|
| D | Flink + Managed Flink | **ship parcial entregue**: artifact contract, extractor, unresolved, rules, fixtures, analyzer, skill, specialist e routing; runtime matrix/collector/functional validation permanecem lacunas |
| E | Glue Streaming + RTM | job/Terraform cross-artifact, runtime guard, capability evidence e rules |
| F | CDC + Debezium + DMS + Schema | **CDC + Schema Registry parciais entregues**: config/event analyzers, contract facts, rules, fixtures, CLI/MCP, skill, specialist e routing; collectors, matriz completa, consumidores cross-artifact e validação funcional permanecem |
| G | Iceberg streaming + observability + lineage + SLO + FinOps | **composição offline parcial entregue**: streaming→Iceberg e progresso→Kafka/Kinesis; collectors, lineage/SLO/FinOps e correlação temporal de longo período permanecem lacunas |
| H | Event-driven + architecture decision + agents/skills/routing | **event-driven parcial entregue**: requirements→facts→candidates→constraints→ADR ainda falta |
| I | Delta/Hudi/Redshift and P2 knowledge | matrices/evals e artefacts somente onde existir caminho determinístico |
| J | security, failure fixtures, integration, performance, packaging and all gates | full suite, package/install/CLI/MCP smoke, security/economy review |

## Regra de conclusão

O prompt só pode ser marcado fechado quando cada domínio P0 tiver o checklist
da seção 50 com `N/A + motivo` onde aplicável, cada wave tiver SDD `ship` verde
e o relatório final separar capacidade comprovada de `unresolved`. Esta matriz
continua deliberadamente aberta até essas evidências existirem.
