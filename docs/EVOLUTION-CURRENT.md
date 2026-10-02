# SparkForge AWS — mapa de evolução atual

**Atualizado em:** 2026-10-02  
**Base técnica de referência:** `cef138c`; fechamento documental corrente:
`7a1290d`
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
   Flink/Managed Flink, Glue Streaming/RTM, CDC, DMS, Debezium, Schema Registry,
   Iceberg, EventBridge/Pipes/SQS/SNS, observabilidade, serving e runtime matrix.
4. **Forge Lab / Digital Twin:** fábrica de evidências reproduzíveis com DSL,
   Compose/Testcontainers, faults allowlisted, oracle independente, receipts e
   tier AWS explícito.

O núcleo continua offline e não chama LLM, SDK de provider, AWS ou Docker durante
extração, julgamento, decisão ou verificação de contrato.

## SDD e prompts de evolução

`sparkforge sdd status --repo .` encontrou **59 features** após este fechamento:
**57 `ship/done`**, uma feature em `plan/ready` (`FORGE_LAB_DIGITAL_TWIN`) e
uma em `ship/draft`
(`INTEGRACAO_USUARIO`). Templates não entram como feature.

| Frente | Features entregues | Estado documentado |
|---|---|---|
| Nova janela / Data Platform Control Plane | `PLATFORM_INTELLIGENCE_GRAPH`, `PLATFORM_INTELLIGENCE_EVALS`, `OPEN_LAKEHOUSE_CATALOG`, `DATA_OBSERVABILITY_SRE`, `ORCHESTRATION_CONTROL_PLANE`, `ANALYTICS_ENGINEERING_MICROSCOPE`, `DATA_PLATFORM_ECOSYSTEM`, além dos fechamentos de decisão e governança | Entregue; ativação produtiva do Decision Plane continua opt-in e `shadow` por padrão |
| Streaming / real-time / CDC | `STREAMING_REALTIME_DATA_PLATFORM`, `STREAMING_TRANSPORT_DIAGNOSTICS`, `STREAMING_TEMPORAL_EVIDENCE`, `STREAMING_ICEBERG_TEMPORAL`, `STREAMING_SLO_EVALUATION`, `STREAMING_SLO_TRANSPORT_EVALUATION`, `STREAMING_FLINK_PLATFORM`, `STREAMING_CDC`, `STREAMING_GLUE_RTM`, `STREAMING_SCHEMA_REGISTRY`, `STREAMING_INTEGRATIONS_AND_CHECKPOINTS`, `STREAMING_READ_ONLY_COLLECTORS`, `STREAMING_RUNTIME_MATRIX`, `STREAMING_STRUCTURED_REVIEW`, `STREAMING_LAKEHOUSE_OBSERVABILITY`, `STREAMING_OPERATIONS_AND_SERVING`, `STREAMING_ARCHITECTURE_DECISION`, `EVENT_DRIVEN_ARCHITECTURE` | Entregue como contratos e diagnósticos offline; progresso→Iceberg tem snapshots granulares e janela temporal pareada, progress→SLO cobre progress/Kafka/Kinesis e separa `met`, `violated` e `unresolved`; evidência live, replay e benchmark permanecem explicitamente `unresolved` quando não fornecidos |
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
  batches ou transporte (`kafka.lag`/`kinesis.shard`), com identidade, unidade e
  janela cobertas; não calcula p95/freshness nem prova saúde end-to-end;
- endpoint live de Kafka Connect, Kafka Streams, OpenLineage e métricas temporais
  de broker/grupo;
- replay funcional, execução Spark/Flink real, benchmark de latência/throughput
  e validação end-to-end;
- atribuição de FinOps por transport/process/runtime/sink e eficácia runtime de
  IAM/KMS/VPC/resource policies;
- snapshots regionais/managed runtime ausentes, que devem sair `unresolved`.

O comportamento correto para cada lacuna é `N/A + motivo`, fact
`*.unresolved` ou recusa nomeada; nenhuma lacuna é preenchida por inferência.

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
| Suíte final do fechamento Forge Lab | 14301 coletados; 14287 passed; 14 skipped |
| Docs de streaming | 137 passed no lote documental de coverage/referências/surface/status; inclui cobertura de SLO de transporte e guias operacionais |
| Economia/contexto | 191 passed no lote funcional; 46 passed em parity/surface |
| Extração e fixtures | SLO observado: facts/composição/ops/CLI/MCP/goldens verdes; transporte SLO: 24 testes de fatos e 18 no lote CLI/goldens, incluindo recusa de séries misturadas; snippet measure adicional: 4 passed |
| Janela temporal | 980 testes focados; 1193 gates de catálogo/docs/knowledge e 769 gates de runtime-scope |
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
