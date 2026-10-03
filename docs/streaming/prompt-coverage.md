# Cobertura auditada de `prompt_evo_streaming.md`

Data da auditoria: 2026-10-02. Esta matriz foi escrita depois de executar
`sparkforge sdd status`, `sparkforge sdd check` nas features de streaming e
`sparkforge code sync`; ela mede artefatos existentes, não menções em Markdown.

O mapa transversal das três evoluções do repositório está em
[`docs/EVOLUTION-CURRENT.md`](../EVOLUTION-CURRENT.md). Esta página permanece
especializada em streaming e conserva `N/A + motivo` onde falta runtime, janela,
endpoint, credencial ou workload reais.
O inventário de commits, features e provas compartilhadas está em
[`docs/DELIVERY-LEDGER.md`](../DELIVERY-LEDGER.md).

## Estado atual auditado após as waves implementadas

| Capability | Nível medido | Evidência atual | Lacuna para P0/P1 |
|---|---|---|---|
| Structured Streaming | `diagnosable` | `sparkforge/facts/pyspark_ast.py`, `facts/streaming.py`, `facts/streaming_integrations.py`, `sparkforge/collect/streaming.py`, `rules/catalog/streaming.yaml`, analyzers, collector read-only e `skills/review-structured-streaming` | progress series agora resume span, duração, memória do state e watermark com `SF-STREAM-013`/`SF-STREAM-014`; execução Spark, replay, benchmark e validação funcional continuam `N/A + motivo`, e cross-artifact permanece unresolved quando artefato não existe |
| Spark Real-Time | `version-aware` parcial | `knowledge/streaming/runtime-matrix.md` revalidada; separação upstream/runtime gerenciado e limite de `Trigger.RealTime` | capability no runtime observado, guard executável e prova de latência continuam `N/A + motivo` sem workload/runtime |
| Kafka | `fact-aware` parcial | `facts/transport.py` preserva timestamps observados; `facts/streaming_temporal.py`, modo `analyze streaming-composition --mode temporal`, fixtures e regra `SF-STREAMOBS-002` pareiam progresso e lag em dumps | Connect REST, série temporal live de broker/grupo e segurança completa |
| Amazon MSK | `version-aware` parcial | `msk.cluster` em `facts/transport.py`, `collect streaming-integrations`, `knowledge/transport-diagnostics.md`, `knowledge/streaming/runtime-matrix.md` | snapshot regional/broker-type, configuração/rede/segurança/lag temporal |
| Kafka Connect | `fact-aware` parcial | `kafka.connect`, `kafka.connect.task`, `SF-STREAM-008`, fixtures e `sparkforge_analyze_streaming_integrations` | collector REST live, offsets/erros temporais e validação funcional |
| Kafka Streams | `fact-aware` parcial | `kafka.streams`, `kafka.streams.state_store`, `SF-STREAM-009`, fixtures e `sparkforge_analyze_streaming_integrations` | métricas/topologia live e decisão composta contra Spark/Flink |
| Kinesis Data Streams | `fact-aware` parcial | `kinesis.stream/shard/metric` preserva timestamp observado; composição temporal, `SF-STREAMOBS-002`, collectors read-only e goldens cobrem janela offline | CloudWatch temporal live, reshard history, KCL/EFO e série de longa duração |
| Apache Flink | `version-aware` parcial | `facts/flink.py`, `rules/catalog/flink.yaml`, `sparkforge_analyze_flink`, fixtures, `analyze-flink-job` e `knowledge/streaming/runtime-matrix.md` | collector/matriz observada de runtime, savepoints, métricas temporais e validação funcional |
| Managed Service for Apache Flink | `version-aware` parcial | namespace `managed_flink.*`, config/connectors/metrics, unresolved, fixtures, mesmo analyzer e matriz com `UNRESOLVED` explícito | matriz AWS por região/release, IAM/VPC/CloudWatch temporal e validação funcional |
| Glue Streaming | `version-aware` parcial | `facts/glue_streaming.py`, regras RTM, fixtures, CLI/MCP, `review-glue-streaming` e matriz Glue 6.0 | job/Terraform cross-artifact, runtime observado/collector, source/sink e validação funcional |
| Glue Real-Time Mode | `version-aware` parcial | namespace `glue.streaming.*`, restrições/capacidade observadas, rules, unresolved e matriz Glue 6.0 com constraints | collector live, cross-artifact e validação funcional |
| CDC | `diagnosable` parcial | `facts/cdc.py`, regras `SF-CDC`, fixtures de evento/connector/seam/unresolved, CLI/MCP e `review-cdc-replication` | collector/replay temporal, cross-artifact com consumidor e validação funcional |
| AWS DMS | `diagnosable` parcial | namespace `dms.*`, `collect streaming-integrations`, task/endpoint/mapping/stats/unresolved, rules e fixtures | matriz de versões, logs temporais e recovery funcional |
| Debezium | `diagnosable` parcial | namespace `debezium.*`, config/status/schema-history/tombstone/unresolved, rules e fixtures | collector Kafka Connect, matriz de versões, offsets/DLQ e replay funcional |
| Schema Registry/data contracts | `diagnosable` parcial | `facts/schema_registry.py`, `rules/catalog/schema_registry.yaml`, fixtures `schema_registry`, `sparkforge_analyze_schema_registry`, `review-cdc-replication` | collectors/live registry, matriz completa de formato/versão, consumidores cross-artifact e validação funcional |
| Streaming + Iceberg | `diagnosable` parcial | `facts/iceberg_metadata.py` emite `iceberg.snapshot`, `facts/streaming_iceberg_temporal.py` compõe janela `StreamingQueryProgress`→`committed_at`, `analyze streaming-composition --mode iceberg_temporal`, regras `streaming_iceberg.yaml`, fixtures e goldens; avaliação SLO observada existe no progress e sink por `mode=slo` | collectors/live lineage, SLO específico de commit, FinOps e validação causal/funcional permanecem lacunas |
| Delta/Hudi | `knowledge-aware` parcial | `streaming_ops.lakehouse`, `knowledge/streaming-format-serving-matrix.md`, fixtures e matriz de formatos | runtime/feature compatibility e collectors ficam P1/P2 |
| Event-driven architecture | `diagnosable` parcial | `facts/event_driven.py`, regras `SF-EVENT`, fixtures, `analyze event-driven`, MCP, skill, routing e SDD | collector live, Step Functions, teste temporal de entrega/replay e decisão vs streaming |
| Streaming observability | `diagnosable` parcial | progress/transport/sink facts, `facts/streaming_composition.py`, `facts/streaming_temporal.py`, `facts/streaming_slo.py`, `facts/streaming_ops.py`, analyzers, collectors read-only, `mode=slo` para progress/sink/Kafka/Kinesis, `SF-STREAMOBS-002`, `SF-STREAM-011` e `SF-STREAM-012` | collectors temporais de série longa, freshness/p95 e correlação live continuam lacunas; sink usa `num_output_rows` ligado a batch, e OpenLineage offline já tem fact, sem endpoint live |
| Streaming FinOps | `diagnosable` parcial | `streaming.finops`, `SF-STREAM-005`, CLI/MCP, fixtures e `knowledge/streaming-operations.md` | CUR/CloudWatch temporal e atribuição por transport/process/runtime/sink |
| Streaming security | `diagnosable` parcial | `streaming.security`, redaction, `SF-STREAM-006`, CLI/MCP e fixtures | IAM/KMS/VPC/resource-policy collectors e eficácia runtime |
| Real-time analytics/serving | `knowledge-aware` parcial | `streaming.serving`, `knowledge/streaming-format-serving-matrix.md`, matriz Redshift/ClickHouse/Pinot/Druid/Trino | collectors/evals por sistema e benchmark de latência/throughput |
| Architecture decision support | `diagnosable` parcial | `sparkforge architecture streaming`, matriz de candidatos, fixtures, skill, ADR e contrato operacional | integrar facts observados de runtime/serving, custo/SLO/security e validação experimental |

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
- Wave I parcial: contrato operacional offline para SLO, FinOps, segurança com
  redaction, serving e formatos lakehouse; regra, CLI/MCP, fixtures, skill,
  conhecimento e SDD ship. Compatibilidade runtime, collectors e benchmark
  permanecem explicitamente fora.
- Wave J parcial: contrato offline para checkpoint metadata, Kafka Connect,
  Kafka Streams e OpenLineage; facts, unresolved, quatro rules P1, fixtures
  completas/incompletas, analyzer CLI/MCP, conhecimento, superfície e SDD ship.
  OpenLineage offline está coberto por fact; collector live, replay temporal,
  benchmark e eficácia end-to-end permanecem
  `N/A + motivo` por dependerem de endpoint, credencial, janela e workload reais.
- Wave K parcial: collector AWS read-only para checkpoint S3, Glue Streaming,
  Kinesis, MSK e DMS, com redaction, cache por hash, manifesto, CLI/MCP e
  testes com clientes falsos. Connect REST, Kafka Streams runtime, OpenLineage
  live, lag temporal, replay e benchmark continuam `N/A + motivo`.
- Wave L: workflow dedicado `review-structured-streaming`, eval, validador de
  evidence, coordenador, mirrors e SDD ship para source/progress/checkpoint;
  execução Spark, replay e benchmark continuam `N/A + motivo` por dependerem de
  workload/runtime real.
- Wave M: `STREAMING_SLO_TRANSPORT_EVALUATION` estende `mode=slo` para séries
  diretamente observadas de `kafka.lag` e `kinesis.shard`, com
  `transport_key`, unidades canônicas, timestamps timezone-aware, janela
  coberta, goldens Kafka/Kinesis, paridade CLI/MCP e unresolved fail-closed.
  Não calcula p95/freshness, não agrega grupos/shards, não usa CloudWatch live e
  não prova saúde end-to-end.

## Fechamentos adicionados nesta atualização

- `STREAMING_CDC`: facts de Debezium, DMS, eventos, seams e blind spots,
  regras, fixtures, CLI/MCP, skill, routing e ship SDD.
- `STREAMING_GLUE_RTM`: contrato offline de Glue Streaming e Real-Time Mode,
  restrições de estado, capacidade e runtime, com unresolved explícito.
- `STREAMING_SCHEMA_REGISTRY`: contrato/diff estrutural de compatibilidade,
  auto-register, políticas ausentes, fixtures, analyzer e ship SDD.
- `STREAMING_INTEGRATIONS_AND_CHECKPOINTS`: checkpoint metadata, Kafka
  Connect, Kafka Streams e OpenLineage com facts separados e limites
  temporais preservados.
- `STREAMING_READ_ONLY_COLLECTORS`: coleta AWS read-only versionada para
  checkpoint S3, Glue Streaming, Kinesis, MSK e DMS, com cache por hash,
  manifesto e redaction.
- `STREAMING_RUNTIME_MATRIX`: matriz upstream/managed/observed com estados
  `VERIFIED`, `UNRESOLVED` e `N/A + motivo`; MSK e Managed Flink continuam
  unresolved sem snapshot regional/managed local.
- `STREAMING_STRUCTURED_REVIEW`: workflow evidence-first, eval, validador,
  coordenador e mirrors sincronizados.
- `STREAMING_ARCHITECTURE_DECISION` e `EVENT_DRIVEN_ARCHITECTURE`: decisão
  por constraints, ADR unresolved, EventBridge/Pipes/SQS/SNS, routing e ship.
- `STREAMING_FLINK_PLATFORM`, `STREAMING_LAKEHOUSE_OBSERVABILITY`,
  `STREAMING_OPERATIONS_AND_SERVING` e `STREAMING_REALTIME_DATA_PLATFORM`:
  relatórios build/ship regularizados e hashes SDD atualizados.
- `GLUE_DQ_ADVANCED_GOVERNANCE_GAPS` e
  `LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS`: ships SDD adicionados para as
  decisões de governança offline, sempre fail-closed.
- `TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH`: habilitadores transversais para
  medir contexto e ligar workspace/semantic graph sem inferir tokens, custo ou
  telemetria de provider.
- `STREAMING_TEMPORAL_EVIDENCE`: modo temporal no compositor existente, timestamps
  observados em Kafka/Kinesis, pareamento declarativo, unresolved, regra P1,
  fixtures Kafka/Kinesis, CLI/MCP e uso compacto com `detail_level`.
- `STREAMING_ICEBERG_TEMPORAL`: fatos granulares `iceberg.snapshot`, janela
  temporal entre progresso e commits Iceberg, `SF-STREAMICE-002`, unresolved,
  fixtures append/non-append/incompleta, CLI/MCP, skill e documentação; não
  atribui causalidade, custo ou ganho.
- `STREAMING_SLO_EVALUATION`: `mode=slo` compara targets declarados com
  métricas diretamente observadas em batches Structured Streaming, exige
  identidade/unidade/janela cobertas, separa `met`, `violated` e unresolved,
  adiciona `SF-STREAM-011`/`SF-STREAM-012`, goldens, CLI/MCP, skill e SDD; não
  calcula p95/freshness, custo, causa ou estado live.
- `STREAMING_SLO_TRANSPORT_EVALUATION`: o mesmo comparador avalia `lag` Kafka
  (`kafka.lag`) e `iterator_age_ms` Kinesis (`kinesis.shard`) por
  `transport_key`, somente com timestamps observados e janela coberta; inclui
  fixtures Kafka met, Kinesis violated, identidade ausente, mirrors, knowledge,
  referências e SDD.
- `STREAMING_SINK_SLO_EVALUATION`: `mode=slo` avalia `num_output_rows` de
  `streaming.progress.sink`, liga `batch_id` ao timestamp/query do batch,
  permite `sink_name`, separa met/violated/unresolved e inclui goldens,
  CLI/MCP, skill, knowledge, referências e SDD. Freshness, p95, exactly-once,
  CloudWatch live e causalidade continuam fora do contrato.
- `STREAMING_PROGRESS_OBSERVABILITY_DEPTH`: amplia `streaming.progress.series`
  com span temporal, duração de batch, memória agregada do state e watermark;
  `SF-STREAM-013` detecta watermark parado e `SF-STREAM-014` memória crescente
  somente com runtime e série suficientes. Medidas inválidas continuam
  unresolved; não há threshold, causa, freshness ou claim de performance.

Todos os itens acima passaram os gates globais de skills, referências, surface,
números correntes e bundle offline em 2026-10-02. Isso fecha contratos offline e
documentação; não converte lacunas de execução, replay, benchmark ou endpoint
live em capacidade comprovada.

## Gaps que permanecem para fechar o prompt operacional

| Wave | Escopo | Critério de fechamento |
|---|---|---|
| D | Flink + Managed Flink | **ship parcial entregue**: artifact contract, extractor, unresolved, rules, fixtures, analyzer, skill, specialist e routing; runtime matrix/collector/functional validation permanecem lacunas |
| E | Glue Streaming + RTM | job/Terraform cross-artifact, runtime guard, capability evidence e rules |
| F | CDC + Debezium + DMS + Schema | **CDC + Schema Registry parciais entregues**: config/event analyzers, contract facts, rules, fixtures, CLI/MCP, skill, specialist e routing; collectors, matriz completa, consumidores cross-artifact e validação funcional permanecem |
| G | Iceberg streaming + observability + lineage + SLO + FinOps | **composição/contrato offline ampliado**: streaming→Iceberg, snapshots granulares, janela temporal progresso→Iceberg, progresso→Kafka/Kinesis, SLO sobre progress/sink/Kafka/Kinesis com janela coberta, OpenLineage facts e declarações SLO/FinOps; collectors temporais live, freshness, endpoint live, correlação de longo período e atribuição continuam lacunas |
| H | Event-driven + architecture decision + agents/skills/routing | **entregue parcialmente**: Event-driven e decision engine têm facts/constraints/ADR; integração automática com execução e teste temporal permanecem lacunas |
| I | Delta/Hudi/Redshift and P2 knowledge | **matrizes e facts declarativos entregues**: compatibilidade e serving são knowledge-aware; evals/collectors/benchmark continuam P1/P2 |
| J | security, failure fixtures, integration, performance, packaging and all gates | **contratos offline entregues**: Connect/OpenLineage/checkpoint/Streams, failure goldens, CLI/MCP, SDD e gates; faltam runtime temporal, replay, benchmark e integração live |
| K | collectors read-only AWS | **entregue parcialmente**: checkpoint S3, Glue, Kinesis, MSK e DMS; cache, redaction, manifesto, CLI/MCP e testes; endpoints Connect/Streams/OpenLineage permanecem fora por não haver API AWS universal |

## Regra de conclusão

O prompt só pode ser marcado fechado quando cada domínio P0 tiver o checklist
da seção 50 com `N/A + motivo` onde aplicável, cada wave tiver SDD `ship` verde
e o relatório final separar capacidade comprovada de `unresolved`. Esta matriz
continua deliberadamente aberta até essas evidências existirem.
