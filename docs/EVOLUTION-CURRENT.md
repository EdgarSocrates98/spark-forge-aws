# SparkForge AWS — mapa de evolução atual

**Atualizado em:** 2026-10-03
**Base técnica de referência:** `912eeb9`; fechamento técnico corrente:
`STREAMING_FLINK_TEMPORAL_METRICS`
**Fonte operacional:** `sparkforge sdd status --repo .`

Este é o índice atual das entregas derivadas de `prompt_evo_nova_janela.md`,
`prompt_evo_streaming.md` e `prompt_evo_forge_lab.md`. Documentos de fase e
relatórios antigos continuam preservados como histórico; quando houver conflito,
este mapa e [`docs/superpowers/STATUS.md`](superpowers/STATUS.md) são a leitura
corrente.

O ledger completo, com inventário SDD, commits de fase, provas e lacunas, está
em [`docs/DELIVERY-LEDGER.md`](DELIVERY-LEDGER.md).

## Estado executivo

O SparkForge agora combina quatro camadas operacionais:

1. **Motor determinístico evidence-first:** facts, rules, findings, unresolved,
   runtime guards e composição sem provider.
2. **Control plane agêntico:** decisão shadow/active opt-in, governor, recovery,
   caches bounded, receipts, replay e budget; `shadow` continua padrão.
3. **Plataforma streaming/batch:** Structured Streaming, Kafka/MSK/Kinesis,
   Flink/Managed Flink, Glue Streaming/RTM com correlação efetivo→Terraform,
   CDC, DMS, Debezium, Schema Registry,
   Iceberg, EventBridge/Pipes/SQS/SNS, observabilidade, serving e runtime matrix.
4. **Forge Lab / Digital Twin:** fábrica de evidências reproduzíveis com DSL,
   Compose/Testcontainers, faults allowlisted, oracle independente, receipts e
   tier AWS explícito.

O núcleo continua offline e não chama LLM, SDK de provider, AWS ou Docker durante
extração, julgamento, decisão ou verificação de contrato.

## SDD e prompts de evolução

`sparkforge sdd status --repo .` encontrou **71 features** após este fechamento:
**69 `ship/done`**, uma feature em `plan/ready` (`FORGE_LAB_DIGITAL_TWIN`) e
uma em `ship/draft`
(`INTEGRACAO_USUARIO`). Templates não entram como feature.

| Frente | Features entregues | Estado documentado |
|---|---|---|
| Nova janela / Data Platform Control Plane | `PLATFORM_INTELLIGENCE_GRAPH`, `PLATFORM_INTELLIGENCE_EVALS`, `OPEN_LAKEHOUSE_CATALOG`, `DATA_OBSERVABILITY_SRE`, `ORCHESTRATION_CONTROL_PLANE`, `ANALYTICS_ENGINEERING_MICROSCOPE`, `DATA_PLATFORM_ECOSYSTEM`, além dos fechamentos de decisão e governança | Entregue; ativação produtiva do Decision Plane continua opt-in e `shadow` por padrão |
| Streaming / real-time / CDC | `STREAMING_REALTIME_DATA_PLATFORM`, `STREAMING_TRANSPORT_DIAGNOSTICS`, `STREAMING_TEMPORAL_EVIDENCE`, `STREAMING_ICEBERG_TEMPORAL`, `STREAMING_SLO_EVALUATION`, `STREAMING_SLO_TRANSPORT_EVALUATION`, `STREAMING_SINK_SLO_EVALUATION`, `STREAMING_PROGRESS_OBSERVABILITY_DEPTH`, `STREAMING_SLO_LATENCY_FRESHNESS`, `STREAMING_KINESIS_TEMPORAL_METRICS`, `STREAMING_MANAGED_FLINK_TEMPORAL_METRICS`, `STREAMING_FLINK_TEMPORAL_METRICS`, `STREAMING_FLINK_PLATFORM`, `STREAMING_FLINK_SOURCE_SINK_ARTIFACTS`, `STREAMING_GLUE_SOURCE_SINK_ARTIFACTS`, `STREAMING_CDC`, `STREAMING_GLUE_RTM`, `STREAMING_GLUE_CROSS_ARTIFACT`, `STREAMING_GLUE_RUNTIME_OBSERVATION`, `STREAMING_SCHEMA_REGISTRY`, `STREAMING_SCHEMA_REGISTRY_COLLECTOR`, `STREAMING_MANAGED_FLINK_COLLECTOR`, `STREAMING_INTEGRATIONS_AND_CHECKPOINTS`, `STREAMING_READ_ONLY_COLLECTORS`, `STREAMING_RUNTIME_MATRIX`, `STREAMING_STRUCTURED_REVIEW`, `STREAMING_LAKEHOUSE_OBSERVABILITY`, `STREAMING_OPERATIONS_AND_SERVING`, `STREAMING_ARCHITECTURE_DECISION`, `EVENT_DRIVEN_ARCHITECTURE` | Entregue como contratos e diagnósticos offline; Schema Registry agora tem coleta Glue read-only de metadata/latest version, paginação, cache, manifesto, limites e unresolved; Flink preserva `flink.source`/`flink.sink`, emite `flink.metric` para observações temporais explícitas e nomeia ausência/shape inválido como unresolved; Glue Streaming agora preserva `glue.streaming.source`/`glue.streaming.sink` com atributos escalares e medidas observadas, além de comparar configuração efetiva com Terraform por nome literal único e runs terminais nos eixos de runtime, distinguindo drift de unresolved; Kinesis coleta cinco métricas stream-level e Managed Flink coleta cinco métricas application-level do CloudWatch com janela explícita, facts temporais e missing/unresolved; progresso→Iceberg tem snapshots granulares e janela temporal pareada, progress→SLO cobre progress/sink/Kafka/Kinesis, `statistic=p95` nearest-rank e `freshness_ms` por `timestamp` + `eventTime.max`, sempre separando `met`, `violated` e `unresolved`; sink usa `num_output_rows` ligado a batch por `batch_id`/`query_name`; enhanced/shard-level, dimensões detalhadas Managed Flink, reshard history, evidência live longa, latência end-to-end implícita, replay e benchmark permanecem explicitamente `unresolved` quando não fornecidos |
| Forge Lab | `FORGE_LAB_PRODUCT` | Entregue e verificado offline; `FORGE_LAB_DIGITAL_TWIN` permanece como registro SDD separado em `plan/ready` |
| Economia observada | `TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH`, `TOKEN_ESTIMATE_UNICO`, `AGENTIC_ECONOMY_COMPLETION` | Entregue; bytes, tokens do provider e custo continuam eixos independentes |
| Governança | `GLUE_DQ_ADVANCED_GOVERNANCE_GAPS`, `LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS` e famílias Lake Formation relacionadas | Entregue offline, fail-closed e com gates focados |

## Streaming: cobertura atual e limite honesto

O índice detalhado está em [`streaming/prompt-coverage.md`](streaming/prompt-coverage.md).
As waves entregaram extratores, facts, regras, fixtures, knowledge, CLI/MCP,
skills, routing, collectors AWS read-only e SDD para os domínios acima.

Ainda não são claims de capacidade de produção:

- correlação temporal longa ou causalidade: a nova janela offline exige query,
  transporte, timestamps e `max_skew_seconds` declarados e só emite finding com
  dois pares observados;
- avaliação SLO offline: `mode=slo` compara métricas diretamente observadas em
  batches, sinks (`num_output_rows`) ou transporte (`kafka.lag`/`kinesis.shard`),
  com identidade, unidade e janela cobertas; aceita `statistic=p95` por
  nearest-rank e `freshness_ms` por `timestamp` + `eventTime.max`; sink exige
  vínculo único com batch por `batch_id`/`query_name`; não prova disponibilidade,
  causalidade ou saúde end-to-end;
- endpoint live de Kafka Connect, Kafka Streams, OpenLineage e métricas temporais
  de broker/grupo;
- replay funcional, execução Spark/Flink real, benchmark de latência/throughput
  e validação end-to-end;
- atribuição de FinOps por transport/process/runtime/sink e eficácia runtime de
  IAM/KMS/VPC/resource policies;
- Glue Streaming agora tem observação offline de runs terminais e facts
  explícitos de source/sink; collector live adicional e validação funcional
  continuam `N/A + motivo`.
- Apache Flink upstream agora tem facts explícitos de source/sink e
  `flink.metric` para observações temporais presentes no artifact, com
  unresolved para ausência/formato inválido; collector live, runtime observado,
  savepoints, série longa, exactly-once e validação funcional continuam `N/A + motivo`.
  Managed Flink tem, separadamente, janela CloudWatch bounded de cinco métricas
  application-level em `managed_flink.metric`.
- snapshots regionais/managed runtime ausentes, que devem sair `unresolved`.
- Kinesis agora possui coleta temporal bounded no collector existente. Ela exige
  `metrics_start`, `metrics_end` e período válido, consulta somente as cinco
  métricas stream-level declaradas em `knowledge/transport-diagnostics.md` e
  não habilita enhanced monitoring. Shard-level, reshard history, KCL/EFO,
  replay, causalidade e série longa continuam `N/A + motivo`.

- Managed Flink agora possui coleta temporal bounded no collector existente.
  Com `metrics_start`, `metrics_end` e `metrics_period`, o artifact preserva
  cinco métricas application-level do namespace `AWS/KinesisAnalytics`, a
  dimensão `Application`, observações timestamped, unidade/estatística,
  resposta raw e missing/unresolved; repetição do mesmo artifact é cache hit
  sem AWS. Task/Operator/Parallelism, job plan, conectores efetivos, IAM,
  runtime regional e validação funcional continuam `N/A + motivo`.

O comportamento correto para cada lacuna é `N/A + motivo`, fact
`*.unresolved` ou recusa nomeada; nenhuma lacuna é preenchida por inferência.

`STREAMING_FLINK_TEMPORAL_METRICS` fecha o contrato offline de pontos temporais
upstream: `metrics`/`metrics.observations` exige nome, valor numérico e
timestamp textual, preserva atributos escalares e não infere epoch. A feature
não cria tool, collector live, série longa ou conclusão de saúde.

`STREAMING_MANAGED_FLINK_COLLECTOR` fecha a coleta read-only da configuração
observada de uma aplicação Managed Flink via `DescribeApplication`, com artifact
versionado, cache offline-first, manifesto SHA-256, CLI/MCP, análise
`managed_flink.*`; `STREAMING_MANAGED_FLINK_TEMPORAL_METRICS` adiciona o recorte
bounded de cinco métricas application-level e limites explícitos para conectores
efetivos, job plan, IAM e validação funcional.

## Forge Lab / Digital Twin

O produto entregue é CLI-first e plan-only por padrão:

- registry versionado em `lab/versions.yaml`, sem `latest` e com digest para
  execução real;
- Golden 20 em `lab/scenarios/golden.yaml`, 11 componentes e 240 ações compiladas;
- geradores determinísticos de dataset e workload, separados da taxa de chegada;
- Compose e Testcontainers usando a mesma DSL e o mesmo plano;
- faults allowlisted, probes Spark/Kafka/Flink/Iceberg/CDC/Prometheus/OTel;
- artefatos SHA-256, receipt content-addressed, oracle independente e promoção
  revisada de fixture;
- equivalência Spark/Flink/Trino/DuckDB e tier AWS L3 com region/owner/TTL/budget/
  prefix/tags/confirmation explícitos.

Prova de contrato: `sparkforge lab verify --repo .` retornou `valid: true`.
Execução mutável local exige `--execute --confirm`; verificação offline não inicia
Docker e não prova performance, custo, capacidade cloud ou semântica AWS.

Detalhe: [`guia/forge-lab.md`](guia/forge-lab.md) e
[`knowledge/forge-lab-product.md`](knowledge/forge-lab-product.md).

## Economia e observabilidade do contexto

O grafo observado e a economia local agora preservam:

- profiles `economy`, `balanced` e `deep`, com caps por capability, skill e
  knowledge;
- `payload_bytes` medidos pelo SparkForge;
- `provider_tokens` somente quando transcript do host fornece usage;
- `cost_basis` separado, sem converter bytes em tokens ou dólares;
- workspace/semantic graph com refresh incremental, fingerprints, relações
  declaradas e `unresolved` para evidência ausente;
- benchmark determinístico de 15 casos pelo comando
  `python scripts/check_token_efficient_bench.py`.

Resultado do último check do benchmark: `suite=token-efficient-matrix`,
`baseline_id=local-deterministic-v1`, `cases=15`. Isso valida o envelope e a
reprodutibilidade; não é claim de economia financeira nem de tokens de provider.

## Evidência de validação

| Gate | Resultado registrado |
|---|---|
| Forge Lab | `valid: true`, 11 componentes, 20 cenários, 240 ações |
| Coleta atual de testes | **14496** testes coletados em 2026-10-03; Flink temporal: **11** unitários, **7** goldens, **69** kinds, documentação **196** e reachability **946** passed; esta frente não executou a suíte completa |
| Suíte final do fechamento Forge Lab | 14301 coletados; 14287 passed; 14 skipped; resultado histórico, não reexecutado após Flink temporal |
| Docs de streaming | cobertura documental Glue source/sink adicionada nesta wave; Flink source/sink acrescentou 83 testes no lote de facts/goldens/kinds; observação Glue runtime acrescentou 9 testes de contrato e 5 goldens/docs/corpus; inclui sink SLO, progress observability depth, p95/freshness SLO, referências geradas e mirrors |
| Economia/contexto | 191 passed no lote funcional; 46 passed em parity/surface |
| Extração e fixtures | SLO observado: facts/composição/ops/CLI/MCP/goldens verdes; transporte SLO: 24 testes de fatos e 18 no lote CLI/goldens, incluindo recusa de séries misturadas; sink SLO: 22 testes de fatos, 2 de aceitação e 3 goldens; progress observability depth: 2 testes de facts, 1 de regras, 35 goldens e 1 fixture nova; p95/freshness: 74 testes focados no lote combinado e 1 golden novo; snippet measure adicional: 4 passed |
| Janela temporal | 980 testes focados; 1193 gates de catálogo/docs/knowledge e 793 gates de runtime-scope |
| Claims e proveniência | 174 passed, 5 skipped |
| Checks globais | skills, referências, surface lock, status numbers, bundle offline e claims sem divergência |

Os resultados acima são evidência de contratos e regressão local. Não significam
CI completo atual, benchmark cloud, saving financeiro ou validação de runtime
gerenciado sem o artefato correspondente.

## Pendências que permanecem abertas

1. `INTEGRACAO_USUARIO` continua draft porque o SDD recusa
   `hypothesis_open_at_ship` e `registry_unchecked verify_wheel`; não se deve
   publicar a integração como pronta sem verificar o wheel e uma CLI real do host.
2. `FORGE_LAB_DIGITAL_TWIN` tem plano SDD pronto, mas não deve ser contado como
   um segundo ship enquanto não houver build/ship próprio; o produto entregue é
   `FORGE_LAB_PRODUCT`.
3. Streaming live, replay, benchmark e validação funcional dependem de
   workload/runtime/credencial reais e seguem `N/A + motivo` até haver receipt.
4. `activation_ready` do Decision Plane permanece `false`; `shadow` e o router
   legado são o rollback target.

## Manutenção documental

Depois de uma entrega, atualizar nesta ordem:

```powershell
sparkforge sdd status --repo .
python scripts/gen_reference_docs.py --check
python scripts/sync_skills.py --check
python scripts/check_surface_lock.py
python scripts/check_status_numbers.py --strict
python scripts/verify_offline_bundle.py --check
python scripts/check_vnext_claims.py
```

Se a mudança alterar código, aplicar também os gates de
[`gates-por-mudanca.md`](gates-por-mudanca.md). Histórico permanece imutável;
estado atual entra neste mapa, em `STATUS.md` e no documento de domínio afetado.
