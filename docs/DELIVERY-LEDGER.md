# SparkForge AWS — ledger de entrega das evoluções

**Atualizado em:** 2026-10-02  
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

O status atual registra **58 features**:

- **56** em `ship/done`;
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
STREAMING_CDC, STREAMING_FLINK_PLATFORM, STREAMING_GLUE_RTM,
STREAMING_ICEBERG_TEMPORAL,
STREAMING_SLO_EVALUATION,
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
- CDC: Debezium, AWS DMS, eventos, posições, transações, tombstones, schema
  history, seams snapshot/CDC e blind spots.
- Schema Registry/data contracts: compatibilidade, evolução, diff estrutural,
  auto-register e políticas ausentes.
- Checkpoints, Kafka Connect, Kafka Streams e OpenLineage como facts separados;
  collectors AWS read-only para checkpoint S3, Glue, Kinesis, MSK e DMS.
- Iceberg/observabilidade: composição offline streaming→Iceberg com snapshots
  granulares e janela temporal progresso→Iceberg, progresso→transporte e janela
  temporal pareada entre progresso e Kafka/Kinesis; `mode=slo` compara SLO
  declarados contra métricas diretamente observadas em progress, emitindo
  `met`, `violated` ou `unresolved` sem inferir causa, custo ou saúde end-to-end;
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

Os commits acima são referências de fase no histórico local. O estado final deve
ser lido pelo código e pelos gates atuais, não por um número isolado de commit.

## Provas registradas

| Prova | Resultado |
|---|---|
| `sparkforge lab verify --repo .` | `valid: true`; 11 componentes, 20 cenários, 240 ações |
| Suíte final do fechamento Forge Lab | 14301 coletados; 14287 passed; 14 skipped |
| Docs e cobertura | 32 passed em `tests/test_reference_docs.py tests/test_docs_coverage.py` |
| Gates de superfície e distribuição | `gen_reference_docs --check`, `sync_skills --check`, surface lock, status numbers e bundle offline verdes |
| Evidência temporal | 980 testes focados; 1193 gates de catálogo/docs/knowledge; 769 runtime-scope; 46 wheel; 4 snippet measure; fixtures Iceberg/Kafka/Kinesis e unresolved persistidos |
| Benchmark de contexto | 15 casos; `baseline_id=local-deterministic-v1`; envelope reproduzível, sem claim de economia |
| Avaliação SLO observada | 16 focused tests; 2 golden checks; 919 gates de catálogo/reachability; 4 snippet-measure; SDD check verde |

Essas provas validam contratos locais, determinismo, paridade e documentação.
Não provam throughput, latência, custo, capacidade cloud, exactly-once, semântica
AWS ou eficácia de uma recomendação em produção.

## Lacunas honestas

1. Execução/replay/benchmark funcional Spark e Flink dependem de workload e runtime.
2. Kafka Connect REST, Kafka Streams runtime, OpenLineage live e métricas
   temporais de broker/grupo exigem endpoint, credencial e janela.
3. A janela temporal curta offline e a avaliação SLO sobre progress estão entregues;
   CloudWatch temporal, reshard, KCL/EFO, FinOps atribuído, SLO de transport/sink
   e SLO de longo período ainda exigem coleta pareada live.
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
