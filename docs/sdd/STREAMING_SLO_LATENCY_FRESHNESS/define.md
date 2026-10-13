---
sdd: 1
feature: STREAMING_SLO_LATENCY_FRESHNESS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_LATENCY_FRESHNESS/explore.md
  sha256: "a26b36a798bbbdbfe4126244a9344de3790260c1300acff72798af0e2df26765"
hypothesis:
  claim: "SLOs declarados com statistic=p95 conseguem comparar p95 observado, e freshness só é emitida quando timestamp e eventTime.max estão pareados e timezone-aware."
  prediction: "Uma série válida produz observed_p95 e status baseado no percentil; progress com eventTime.max produz freshness_ms por batch; timestamp, eventTime ou métrica inválidos permanecem unresolved sem preencher valores."
  experiment: "Adicionar testes vermelhos para derivação temporal, p95, métrica explícita, unidades e lacunas; implementar extrator/compositor; adicionar golden de freshness/p95; executar gates focados e regenerar referências/documentação."
acceptance:
  - id: AC1
    statement: "A declaração streaming.slo aceita statistic=all ou statistic=p95, preserva atributos seguros e recusa estatística desconhecida."
    verified_by: {kind: test, ref: tests/test_facts_streaming_ops.py::test_slo_preserves_statistic_attribute}
  - id: AC2
    statement: "StreamingQueryProgress com timestamp e eventTime.max timezone-aware em todas as observações publica freshness_ms por batch; ausência ou valor inválido não vira zero."
    verified_by: {kind: test, ref: tests/test_facts_streaming.py::test_progress_derives_freshness_only_from_event_time_max}
  - id: AC3
    statement: "O compositor calcula p95 nearest-rank sobre série diretamente observada, mantém source_fact_ids e avalia operador contra observed_p95."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_evaluates_p95_freshness_slo}
  - id: AC4
    statement: "Métrica end_to_end_latency_ms só é aceita quando explicitamente observada; não é derivada de batch duration ou freshness."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_end_to_end_latency_requires_explicit_measurement}
  - id: AC5
    statement: "Golden de SLO p95/freshness cobre met/violated e a validade de fatos/findings permanece determinística."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens}
  - id: AC6
    statement: "Knowledge, skill, prompt coverage, referências e ledger descrevem p95/freshness e seus limites sem afirmar live, causa ou performance."
    verified_by: {kind: command, ref: python scripts/check_status_numbers.py --strict}
success:
  - id: SC1
    metric: "AC1–AC6 verdes; nenhuma ausência temporal é convertida em zero e p95 tem método explicitamente documentado"
    source: "pytest focado, golden de composição, catálogo, referências, status e bundle offline"
out_of_scope:
  - "Collector live CloudWatch/Kafka/Flink/OpenLineage"
  - "Interpolação estatística, confidence interval, tendência longa ou threshold inventado"
  - "End-to-end latency derivada de batch duration ou event-time freshness"
  - "Benchmark, replay Spark, validação funcional e atribuição causal"
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Confirmar no artefato que eventTime.max representa o maior event time da janela observada; o Forge registra a relação, mas não prova semântica do produtor."
  - id: U2
    blocks: [AC6]
    unlock: "Regenerar referências, surface/manifest quando aplicável e números correntes após alteração dos contratos."
change_kinds: [extractor, tool_or_verb, fixture_corpus, knowledge_doc, agent_or_skill, status_numbers]
---

# STREAMING_SLO_LATENCY_FRESHNESS — requisitos
