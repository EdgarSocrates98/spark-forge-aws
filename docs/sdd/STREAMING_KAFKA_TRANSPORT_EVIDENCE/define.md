---
sdd: 1
feature: STREAMING_KAFKA_TRANSPORT_EVIDENCE
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_KAFKA_TRANSPORT_EVIDENCE/explore.md
  sha256: "2c47f8e48a26824168ab28fa5de846851b5efd60ca4363c149306ffcd1438185"
hypothesis:
  claim: "Um dump Kafka com ISR/replication observados e uma série explícita de lag pode gerar dois sinais operacionais evidence-backed sem misturar snapshot, causa ou saúde live."
  prediction: "Uma partição com replication_factor maior que isr_count gera SF-STREAMOBS-003; duas ou mais observações timestampadas da mesma identidade com lag estritamente crescente geram kafka.lag.series e SF-STREAMOBS-004; identidade, timestamp ou quantidade insuficiente geram kafka.unresolved; dump legado sem lag_observations mantém os facts anteriores."
  experiment: "Adicionar testes vermelhos para extração e rules, implementar o resumo compacto, criar goldens de ISR/lag/unresolved, regenerar skill/mirrors/knowledge/locks e executar gates focados sem suite completa."
acceptance:
  - id: AC1
    statement: "O extrator preserva observações Kafka explícitas de lag como kafka.lag e compõe kafka.lag.series somente com identidade completa, lag numérico, timestamp textual timezone-aware e pelo menos duas observações ordenáveis."
    verified_by: {kind: test, ref: tests/test_facts_transport.py::test_kafka_explicit_lag_observations_emit_series_and_reject_insufficient}
  - id: AC2
    statement: "Uma série válida publica observation_count, first_lag, last_lag, delta_lag, monotonic_increase, timestamp span e source fact ids sem declarar causalidade."
    verified_by: {kind: test, ref: tests/test_facts_transport.py::test_kafka_explicit_lag_observations_emit_series_and_reject_insufficient}
  - id: AC3
    statement: "Dump Kafka legado sem lag_observations não produz série inferida nem unresolved de tendência, preservando os facts de snapshot existentes."
    guard: "A guarda passa antes e depois por desenho para evitar que uma feature temporal recuse ou reinterprete dumps Kafka históricos."
    verified_by: {kind: test, ref: tests/test_facts_transport.py::test_kafka_legacy_snapshot_does_not_infer_lag_series}
  - id: AC4
    statement: "SF-STREAMOBS-003 dispara somente quando replication_factor observado é maior que isr_count observado; SF-STREAMOBS-004 dispara somente para série suficiente, monotônica e com delta_lag positivo."
    verified_by: {kind: test, ref: tests/test_streaming_rules.py::test_kafka_transport_rules_require_observed_conditions}
  - id: AC5
    statement: "Goldens Kafka cobrem ISR deficit, série crescente, série não monotônica e blind spots sem preencher zero ou inventar timestamp."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_transport.py::test_transport_fixture_corpus_is_complete}
  - id: AC6
    statement: "Knowledge, skill, coordenador, prompt coverage, SDD, manifest offline, sources lock e números correntes descrevem os facts e limites do contrato."
    verified_by: {kind: command, ref: python scripts/check_status_numbers.py --strict}
success:
  - id: SC1
    metric: "AC1–AC6 verdes; nenhuma finding de ISR ou lag usa ausência, ordem do arquivo ou uma observação isolada como evidência temporal."
    source: "pytest focado de facts/rules/goldens e gates de catálogo, skills, knowledge, referências, status e bundle offline"
out_of_scope:
  - "collector live Kafka/MSK, Kafka Connect REST, CloudWatch ou chamada a broker"
  - "hot partition, causa dominante, throughput, capacidade, disponibilidade, SLO ou custo"
  - "threshold de min.insync.replicas, segurança Kafka/MSK, compatibilidade de versões ou rede"
  - "agregação entre grupos/topics/partitions sem identidade declarada"
  - "série longa, p95, replay, benchmark e validação funcional"
unknowns:
  - id: U1
    blocks: [AC1, AC2]
    unlock: "Artifact real com observações timestampadas e timezone-aware de uma mesma identidade Kafka."
  - id: U2
    blocks: [AC4]
    unlock: "Runtime, min.insync.replicas, acks e eventos do broker para interpretar o sinal de ISR sem atribuir consequência."
  - id: U3
    blocks: [AC6]
    unlock: "Regenerar references, offline manifest, source lock e status depois do novo fact/rule/knowledge."
case_id: null
change_kinds: [extractor, rule, rule_runtime_scope, fixture_corpus, knowledge_doc, agent_or_skill, status_numbers]
---

# STREAMING_KAFKA_TRANSPORT_EVIDENCE — requisitos

Esta feature fecha apenas dois sinais observáveis no analyzer de transporte:
replicação fora do ISR observado e crescimento monotônico em uma série Kafka
explicitamente declarada. O resultado continua offline, compacto e
evidence-first; ausência de endpoint, janela longa, runtime ou causa permanece
unresolved ou fora de escopo.
