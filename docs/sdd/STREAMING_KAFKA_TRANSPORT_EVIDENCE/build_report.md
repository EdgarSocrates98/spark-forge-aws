---
sdd: 1
feature: STREAMING_KAFKA_TRANSPORT_EVIDENCE
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_KAFKA_TRANSPORT_EVIDENCE/plan.md
  sha256: "f6a8d96b75868f900abdad519530d5ae069cd1cfd68d4417967293ee599d54c2"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_transport.py::test_kafka_explicit_lag_observations_emit_series_and_reject_insufficient tests/test_facts_transport.py::test_kafka_legacy_snapshot_does_not_infer_lag_series -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t1-red", exit: 1}
    green: {command: "python -m pytest tests/test_facts_transport.py::test_kafka_explicit_lag_observations_emit_series_and_reject_insufficient tests/test_facts_transport.py::test_kafka_legacy_snapshot_does_not_infer_lag_series -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t1-green", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_streaming_rules.py::test_kafka_transport_rules_require_observed_conditions -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t2-red", exit: 1}
    green: {command: "python -m pytest tests/test_streaming_rules.py::test_kafka_transport_rules_require_observed_conditions -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t2-green", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_transport.py::test_transport_fixture_corpus_is_complete -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t3-node-red", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_transport.py::test_transport_fixture_corpus_is_complete -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t3-node-green", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_docs_coverage.py -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t4-docs", exit: 1}
    green: {command: "python -m pytest tests/test_docs_coverage.py -q -p no:cacheprovider --basetemp .pytest-tmp-kafka-t4-docs2", exit: 0}
  - id: T5
    status: done
    red: {command: "python scripts/check_status_numbers.py --strict", exit: 1}
    green: {command: "python scripts/check_status_numbers.py --strict", exit: 0}
claims:
  - text: "O extrator compõe série Kafka apenas de observações explícitas e preserva o snapshot legado."
    evidence_ref: "tests/test_facts_transport.py::test_kafka_explicit_lag_observations_emit_series_and_reject_insufficient"
  - text: "As regras novas exigem condições observadas de ISR e de crescimento monotônico."
    evidence_ref: "tests/test_streaming_rules.py::test_kafka_transport_rules_require_observed_conditions"
  - text: "O corpus dourado valida facts, findings e determinismo dos oito cenários de transporte, incluindo os dois novos."
    evidence_ref: "tests/test_fixtures_golden_transport.py::test_transport_fixture_corpus_is_complete"
  - text: "Os documentos gerados, mirrors e manifestos passam as guardas de documentação."
    evidence_ref: "tests/test_docs_coverage.py"
  - text: "Os números correntes publicados correspondem às medidas do catálogo, kinds e fixtures."
    evidence_ref: "python scripts/check_status_numbers.py --strict"
change_id: null
---

# STREAMING_KAFKA_TRANSPORT_EVIDENCE — relatório do build

## Desvios do plano

- O gate do corpus revelou que `fixtures/transport/kinesis_positive` estava
  desatualizado: o extrator já emitia `stream_name` em `kinesis.shard`, então o
  golden foi corrigido no mesmo commit de corpus para manter a cobertura
  determinística.
- Goldens foram regenerados pelos verbos CLI de analyze/judge usando paths
  absolutos, preservando ids, procedência e o formato de lista dos goldens.
- Nenhum tool, verb ou collector novo foi criado.

## Revisão

Revisão local de especificação e qualidade conferiu o diff contra define/design:
identidade explícita, timestamps timezone-aware, ausência fail-closed, ids de
evidência, actions de baseline/investigação e compatibilidade do snapshot legado.
O escopo não inclui causa, saúde live, throughput, SLO, custo ou mutação.

## Resultado

T1–T5 concluídas com red real antes do green. Os gates focados de facts, rules,
goldens, kinds/regras, docs, mirrors, referências, knowledge, surface, status e
SDD ficaram verdes. A suíte completa não foi executada nesta frente.
