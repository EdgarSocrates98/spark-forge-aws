# SparkForge AWS — ledger de entrega das evoluções

**Atualizado em:** 2026-10-03
**Fonte de estado:** `sparkforge sdd status --repo .`  
**Escopo:** `prompt_evo_nova_janela.md`, `prompt_evo_streaming.md` e
`prompt_evo_forge_lab.md`

Este ledger é a leitura curta do que foi entregue. O detalhe técnico permanece
nos `ship.md`, no catálogo de regras, nas skills, no conhecimento e nos guias
referenciados aqui. Ele não transforma contrato offline em capacidade live.

## Resultado executivo

| Frente | Entrega atual | Estado |
|---|---|---|
| Nova janela / plataforma de dados | control plane agêntico, grafo de inteligência, catálogo lakehouse, observabilidade/SRE, orquestração, analytics engineering, ecossistema de dados, governança e economia medida | Entregue offline |
| Streaming / real-time / batch | Structured Streaming, Kafka/MSK/Kinesis, Flink, Glue Streaming/RTM, CDC/Debezium/DMS, Schema Registry, Iceberg, eventos, serving, SLO/FinOps/security, collectors read-only e matrizes de runtime | Entregue como contratos e diagnósticos offline |
| Forge Lab | DSL, registry, Golden 20, geradores, faults allowlisted, Compose/Testcontainers, probes, oracle, receipts, promoção de fixtures e tier AWS explícito | `FORGE_LAB_PRODUCT` entregue; Digital Twin separado em `plan/ready` |
| Economia de contexto | profiles, caps, payload bytes, transcript usage, refresh incremental, grafo semântico, receipts e benchmark determinístico | Entregue; economia financeira/provider continua não inferida |

O produto está pronto para auxiliar projetos streaming e batch com evidência
reproduzível, julgamento rastreável e especialistas roteáveis. Execução Spark/Flink,
replay, endpoints live, benchmark cloud e validação funcional continuam exigindo
artefatos reais; quando ausentes, o SparkForge retorna `unresolved`, `N/A + motivo`
ou recusa nomeada.

## Estado SDD

O status atual registra **66 features**:

- **64** em `ship/done`;
- **1** em `plan/ready`: `FORGE_LAB_DIGITAL_TWIN`;
- **1** em `ship/draft`: `INTEGRACAO_USUARIO`, bloqueada por
  `hypothesis_open_at_ship` e `registry_unchecked`.

### Features entregues

```text
AC_VERMELHO, AGENTIC_ECONOMY_COMPLETION, AIRFLOW_DAG,
ANALYTICS_ENGINEERING_MICROSCOPE, CONFIG_OCA, CRITERIO_DE_DOMINIO,
DATABRICKS_PHOTON_PLAN, DATABRICKS_SPARK, DATA_OBSERVABILITY_SRE,
DATA_PLATFORM_ECOSYSTEM, EVENT_DRIVEN_ARCHITECTURE, FORGE_LAB_PRODUCT,
GLUE_DQ_ADVANCED_GOVERNANCE_GAPS, GLUE_TERRAFORM,
LAKE_FORMATION_FGAC_FTA_EVOLUTION, LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS,
LAKE_FORMATION_OPERATIONAL_CLOSURE, LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION,
LAKE_FORMATION_PROMPT_GAP_AUDIT, LF_FTA_DECLARADO, LF_GRANTS,
OPEN_LAKEHOUSE_CATALOG, ORCHESTRATION_CONTROL_PLANE,
PLATFORM_INTELLIGENCE_EVALS, PLATFORM_INTELLIGENCE_GRAPH, SDD_ENDURECIMENTO,
SDD_EVAL, SDD_MIGRATION, SDD_OPERATOR, SDD_OPERATOR_DURAVEL, SDD_SKILLS,
SDD_SKILLS_REVISAO, SFN_HISTORY, SFN_TENTATIVA, SF_STUBS,
SKILLS_QUALITY_EVOLUTION, STEP_FUNCTIONS, STREAMING_ARCHITECTURE_DECISION,
STREAMING_CDC, STREAMING_FLINK_PLATFORM, STREAMING_FLINK_SOURCE_SINK_ARTIFACTS,
STREAMING_GLUE_SOURCE_SINK_ARTIFACTS, STREAMING_GLUE_RTM,
STREAMING_GLUE_CROSS_ARTIFACT, STREAMING_GLUE_RUNTIME_OBSERVATION,
STREAMING_ICEBERG_TEMPORAL,
STREAMING_SLO_EVALUATION,
STREAMING_SLO_TRANSPORT_EVALUATION,
STREAMING_SINK_SLO_EVALUATION,
STREAMING_PROGRESS_OBSERVABILITY_DEPTH,
STREAMING_SLO_LATENCY_FRESHNESS,
STREAMING_INTEGRATIONS_AND_CHECKPOINTS, STREAMING_LAKEHOUSE_OBSERVABILITY,
STREAMING_OPERATIONS_AND_SERVING, STREAMING_READ_ONLY_COLLECTORS,
STREAMING_REALTIME_DATA_PLATFORM, STREAMING_RUNTIME_MATRIX,
STREAMING_SCHEMA_REGISTRY, STREAMING_STRUCTURED_REVIEW,
STREAMING_TEMPORAL_EVIDENCE, STREAMING_TRANSPORT_DIAGNOSTICS,
TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH,
TOKEN_ESTIMATE_UNICO, TOOLS_OK
```

Os dois itens que não estão nessa lista são deliberadamente abertos: o Digital
Twin aguarda build/ship próprio, e a integração do usuário aguarda verificação
do wheel e de uma CLI real do host.

## Entregas por frente

### Plataforma de dados e control plane

- Facts, findings, regras, `unresolved`, runtime guards, composição, cases,
  gates fail-closed, assinatura de correspondência, handoff e SDD determinístico.
- Decision Plane declarativo em shadow mode, com `validate`, `shadow`, `compare`,
  `benchmark` e `receipt`; `activation_ready` permanece `false`.
- Roteamento para coordenadores e executores, playbooks quando dispatch não existe,
  specialists de Spark, AWS, lakehouse, segurança, governança, analytics e
  engenharia de plataforma.
- Code Intelligence, grafo de conhecimento e economia de contexto sem importar
  SDK de provider no core.
- Glue, EMR EC2/Serverless/EKS, Databricks declarado/Photon, migração, Terraform,
  Airflow, Step Functions, Control-M, Lake Formation e IAM com fronteiras
  explícitas.

### Streaming, real-time e CDC

- Structured Streaming: source/progress, watermark, state, sink, checkpoint e
  review evidence-first.
- Transporte: Kafka, MSK, Kinesis, lag, partições, shards, métricas e identidade
  declarada para composição.
- Flink e Managed Flink, Glue Streaming e Glue Real-Time Mode, com matrizes de
  runtime e limites managed/upstream.
- Glue Streaming efetivo versus Terraform: `fuse` compara por nome literal único
  versão, RTM, linguagem e workers; `SF-GLUESTREAM-004` sinaliza drift e
  `SF-GLUESTREAM-005` preserva identidade/valor unresolved.
- Glue Streaming runtime observado: `fuse` compara a definição efetiva com
  `glue.job_run` por nome literal nos eixos `glue_version`, `worker_type` e
  `worker_count`; `SF-GLUESTREAM-006` sinaliza drift e
  `SF-GLUESTREAM-007` preserva ausência de run, identidade ou campo.
- Glue Streaming source/sink: `glue.streaming.source` e
  `glue.streaming.sink` preservam endpoints declarados no dump, atributos
  escalares e medidas numéricas observadas; `glue.streaming.unresolved`
  nomeia ausência, shape inválido ou métrica ausente. Não há rule, collector
  live ou conclusão de saúde nesta wave.
- CDC: Debezium, AWS DMS, eventos, posições, transações, tombstones, schema
  history, seams snapshot/CDC e blind spots.
- Schema Registry/data contracts: compatibilidade, evolução, diff estrutural,
  auto-register e políticas ausentes.
- Checkpoints, Kafka Connect, Kafka Streams e OpenLineage como facts separados;
  collectors AWS read-only para checkpoint S3, Glue, Kinesis, MSK e DMS.
- Iceberg/observabilidade: composição offline streaming→Iceberg com snapshots
  granulares e janela temporal progresso→Iceberg, progresso→transporte e janela
  temporal pareada entre progresso e Kafka/Kinesis; `mode=slo` compara SLO
  declarados contra métricas diretamente observadas em progress, `kafka.lag`,
  `kinesis.shard` ou `num_output_rows` em `streaming.progress.sink` ligado a
  batch por `batch_id`/`query_name`, emitindo `met`, `violated` ou `unresolved`
  sem inferir causa, custo ou saúde end-to-end;
  `streaming.progress.series` resume span temporal, duração de batch, memória
  agregada de state e watermark quando há série completa, e `SF-STREAM-013/014`
  registram somente sintomas observados de watermark parado e memória crescente;
  `mode=slo` aceita `statistic=p95` por nearest-rank e `freshness_ms` por
  `timestamp - eventTime.max`, enquanto latência end-to-end exige campo explícito;
  timestamps/watermarks inválidos permanecem unresolved nomeados;
  operações, serving, SLO, FinOps, security/redaction,
  EventBridge/Pipes/SQS/SNS e decisão arquitetural por constraints.

### Forge Lab

- Registry versionado com digest; Golden 20; 11 componentes; 240 ações compiladas.
- DSL única para Compose e Testcontainers, com geradores determinísticos de
  dataset/workload, taxa de chegada separada, skew, atraso, duplicidade e faults
  allowlisted.
- Probes de Spark, Kafka, Flink, Iceberg, CDC, Prometheus e OTel; artefatos com
  SHA-256, receipts content-addressed, oracle independente e promoção revisada.
- Backends Spark/Flink/Trino/DuckDB e tier AWS L3 com region, owner, TTL, budget,
  prefix, tags e confirmação explícitos.
- CLI plan-only por padrão: mutação local exige `--execute --confirm`; `verify`
  não inicia Docker.

### Documentação, skills e conhecimento

- Guias de instalação, CLI, MCP, agents/skills, extração/julgamento/composição,
  conhecimento/catalog, rigor/handoff, camada agêntica, segurança, espelhos e
  Forge Lab.
- Referências de CLI, MCP, agents e skills geradas do código e protegidas por
  surface lock.
- Knowledge index com contratos de streaming, CDC, runtime, serving, eventos,
  Forge Lab, governança, AWS e plataformas de agentes.
- Mirrors `.claude`, `.agents` e `.github` sincronizados a partir de `skills/` e
  `agents/`; bundle offline com hashes conferidos.

## Commits de fechamento por fase

| Commit | Fechamento |
|---|---|
| `698dcfb` | CDC/Debezium/DMS |
| `312fec1` | Glue Streaming/Real-Time Mode |
| `347c6f1` | Schema Registry/data contracts |
| `800736b` | integrações e checkpoints |
| `4ce3510` | collectors AWS read-only |
| `dd10694` | matriz de runtime streaming |
| `b61f78d` | relatórios de fechamento streaming |
| `04404d8` | ondas de governança e Decision Plane |
| `758ae0b` | economia observada do grafo/contexto |
| `87ee83c` / `ddf35ef` | documentação e ship do Forge Lab |
| `09d6f31` | consolidação transversal da evolução |
| `a626220` | composição temporal offline, regra e goldens Kafka/Kinesis |
| `fab535a` | ship SDD, mirrors, referências, surface lock e documentação temporal |
| `171074b` | facts granulares de snapshots Iceberg, composição temporal, regra, fixtures e schema |
| `fb0f5c5` | SDD ship, mirrors, referências, knowledge, surface lock, status e ledger da correlação temporal Iceberg |
| `2fbf157` | re-stamp final do SDD ship após fechamento do build report |
| `4831844` | alinhamento do SDD e contagens correntes da avaliação SLO |
| `d4a7ba9` | facts, composição, regras, fixtures e portas CLI/MCP da avaliação SLO |
| `a1388ee` | SDD build/ship, knowledge, skills, referências, manifests e documentação transversal da avaliação SLO |
| `1cba6fb` | avaliação SLO direta sobre lag Kafka e iterator age Kinesis, identidade, timestamps, goldens e paridade CLI/MCP |
| `cef138c` | recusa `ambiguous_transport` para impedir mistura de grupos, topics, partições e shards em uma avaliação SLO |
| `08b219a` | SDD ship, knowledge, skills, referências, mirrors, surface lock, offline manifest, status e ledger da avaliação SLO de transporte |
| `1a9bbe3` | atualização do SDD, evolução, status e ledger para a guarda contra séries de transporte misturadas |
| `7a1290d` | atualização transversal de README, guias CLI/MCP/agents, prompt mestre, payload Devin, contagens correntes e documentação de SLO observado |
| `b10751b` | SLO de saída do sink: `num_output_rows`, vínculo `batch_id`/`query_name`, unresolved nomeado, CLI/MCP, goldens e paridade offline |
| `d433caf` | ship SDD e atualização transversal das docs, skills, knowledge, mirrors, referências, manifests, evolução, STATUS e prompt coverage do sink SLO |
| `57ae53d` | SDD explore/define/design/plan da profundidade de observabilidade do progresso |
| `0ea23e1` | extrator temporal, `SF-STREAM-013/014`, testes, fixture e goldens de progresso |
| `d4106b6` | ship SDD, knowledge, skills, mirrors, referências, manifests, surface lock, status e documentação transversal |
| `aedae77` | SDD explore/define/design/plan de p95 e freshness SLO |
| `4ba8177` | facts, compositor, testes e golden de `statistic=p95`, `freshness_ms` e latência explícita |
| `34eb790` | documentação, mirrors, locks e ship report de p95/freshness SLO |
| `ebb567d` | SDD explore/define/design/plan de correlação Glue Streaming/Terraform |
| `e8d42eb` | facts, fuse, regras, fixtures e goldens de cross-artifact Glue |
| `cdc0556` | ship SDD, guias, knowledge, skill, mirrors, referências, locks e ledgers do cross-artifact Glue |
| `79a38db` | facts, fuse, regras, fixtures, goldens e SDD da observação Glue Streaming→runs |
| `2b17519` | documentação transversal, skill/mirrors, knowledge, locks, ledgers e status da observação Glue Streaming |
| `6084a17` | facts explícitos `flink.source`/`flink.sink`, unresolved nomeado, testes unitários e goldens Flink |
| `aa6e133` | SDD explore/define/design/plan/build/ship, docs, skill/mirrors, knowledge, manifest offline, surface lock, status e cobertura do contrato Flink source/sink |
| `f1c9538` | SDD e contrato offline de `glue.streaming.source`/`glue.streaming.sink`, testes, goldens e documentação transversal |

Os commits acima são referências de fase no histórico local. O estado final deve
ser lido pelo código e pelos gates atuais, não por um número isolado de commit.

## Provas registradas

| Prova | Resultado |
|---|---|
| `sparkforge lab verify --repo .` | `valid: true`; 11 componentes, 20 cenários, 240 ações |
| Coleta atual de testes | 14396 testes coletados em 2026-10-02; suíte completa não executada nesta frente |
| Suíte final do fechamento Forge Lab | 14301 coletados; 14287 passed; 14 skipped |
| Docs e cobertura | 137 passed em `tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_surface_lock.py tests/test_status_numbers_gate.py` |
| Gates de superfície e distribuição | `gen_reference_docs --check`, `sync_skills --check`, surface lock, status numbers e bundle offline verdes |
| Evidência temporal | 980 testes focados; Flink source/sink: 8 unitários e 83 em facts/goldens/kinds; observação Glue runtime: 9 testes de contrato, 5 goldens/docs/corpus e 793 runtime-scope; 1193 gates de catálogo/docs/knowledge; 46 wheel; 4 snippet measure; fixtures Iceberg/Kafka/Kinesis/Glue e unresolved persistidos |
| Benchmark de contexto | 15 casos; `baseline_id=local-deterministic-v1`; envelope reproduzível, sem claim de economia |
| Avaliação SLO observada | progress: 16 focused tests; transporte: 24 testes de fatos, 18 no lote CLI/goldens, 3 goldens novos e recusa de séries misturadas; sink: 22 testes de fatos, 2 de aceitação e 3 goldens; progress observability depth: 35 goldens, 1214 gates de catálogo e SDD check verde; p95/freshness: 74 testes focados e golden `slo_p95_freshness` |

Essas provas validam contratos locais, determinismo, paridade e documentação.
Não provam throughput, latência, custo, capacidade cloud, exactly-once, semântica
AWS ou eficácia de uma recomendação em produção.

## Lacunas honestas

1. Execução/replay/benchmark funcional Spark e Flink dependem de workload e runtime; Glue Streaming agora tem observação offline de runs, mas não collector live adicional.
2. Kafka Connect REST, Kafka Streams runtime, OpenLineage live e métricas
   temporais de broker/grupo exigem endpoint, credencial e janela.
3. A janela temporal curta offline e as avaliações SLO sobre progress, sink e
   transporte estão entregues; CloudWatch temporal, reshard, KCL/EFO, FinOps
   atribuído, latência end-to-end sem medida explícita e SLO de longo período
   ainda exigem coleta pareada live.
4. IAM/KMS/VPC/resource policies e snapshots regionais/managed runtime precisam
   do artefato correspondente.
5. `FORGE_LAB_DIGITAL_TWIN` não é ship enquanto não houver build/ship próprio.
6. `activation_ready` permanece `false`; `shadow` e router legado são rollback.

## Como manter este ledger

Após cada fase, atualizar este arquivo e os documentos de domínio, então executar:

```powershell
sparkforge sdd status --repo .
python scripts/gen_reference_docs.py --check
python scripts/sync_skills.py --check
python scripts/check_surface_lock.py
python scripts/check_status_numbers.py --strict
python scripts/verify_offline_bundle.py --check
```

O mapa executivo está em [`EVOLUTION-CURRENT.md`](EVOLUTION-CURRENT.md), o estado
por fase em [`superpowers/STATUS.md`](superpowers/STATUS.md), a cobertura de
streaming em [`streaming/prompt-coverage.md`](streaming/prompt-coverage.md) e o
contrato do laboratório em [`guia/forge-lab.md`](guia/forge-lab.md).
