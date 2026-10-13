---
sdd: 1
feature: STREAMING_FLINK_TEMPORAL_METRICS
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_TEMPORAL_METRICS/plan.md
  sha256: "0d28e4aeaa72372d451ebee8cc06fa05955117707374d1f35a0102793d4a4aa6"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_flink.py::test_flink_temporal_metrics_preserve_observed_value_and_metadata -q --basetemp .pytest-flink-temporal-t1", exit: 1}
    green: {command: "python -m pytest tests/test_facts_flink.py::test_flink_temporal_metrics_preserve_observed_value_and_metadata -q --basetemp .pytest-flink-temporal-t1", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_facts_flink.py::test_flink_temporal_metric_missing_timestamp_is_unresolved -q --basetemp .pytest-flink-temporal-t2", exit: 1}
    green: {command: "python -m pytest tests/test_facts_flink.py::test_flink_temporal_metric_missing_timestamp_is_unresolved -q --basetemp .pytest-flink-temporal-t2", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_facts_flink.py::test_flink_temporal_metrics_invalid_shape_is_unresolved -q --basetemp .pytest-flink-temporal-t3", exit: 1}
    green: {command: "python -m pytest tests/test_facts_flink.py::test_flink_temporal_metrics_invalid_shape_is_unresolved -q --basetemp .pytest-flink-temporal-t3", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete -q --basetemp .pytest-flink-temporal-t4-red", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_flink.py -q --basetemp .pytest-flink-temporal-t4-green", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_reference_docs.py::test_referencia_em_dia -q --basetemp .pytest-flink-temporal-t5-red", exit: 1}
    green: {command: "python -m pytest tests/test_reference_docs.py::test_referencia_em_dia -q --basetemp .pytest-flink-temporal-t5-green", exit: 0}
claims:
  - text: "Observações upstream explícitas preservam nome, valor numérico, timestamp textual e metadados escalares em flink.metric."
    evidence_ref: "tests/test_facts_flink.py::test_flink_temporal_metrics_preserve_observed_value_and_metadata"
  - text: "Timestamp ausente ou inválido não produz métrica parcial nem infere epoch; produz flink.unresolved."
    evidence_ref: "tests/test_facts_flink.py::test_flink_temporal_metric_missing_timestamp_is_unresolved"
  - text: "Shape e valor inválidos produzem unresolved nomeado sem fabricar observação."
    evidence_ref: "tests/test_facts_flink.py::test_flink_temporal_metrics_invalid_shape_is_unresolved"
  - text: "Fixture temporal cobre métrica válida, aliases, metadados escalares e registro sem timestamp no corpus golden."
    evidence_ref: "tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete"
  - text: "Skills, mirrors, referências, knowledge, coverage, manifesto e surface lock descrevem contrato e limites."
    evidence_ref: "tests/test_reference_docs.py::test_referencia_em_dia"
change_id: null
---

# STREAMING_FLINK_TEMPORAL_METRICS — relatório do build

## Resultado

Build concluído em T1–T5. O extrator upstream aceita somente observações
temporais presentes no artifact: nome, valor numérico e timestamp textual. O
contrato emite `flink.metric` com atributos escalares e transforma shape,
nome, valor ou timestamp inválido em `flink.unresolved`. Artifacts antigos sem
`metrics` mantêm o conjunto anterior de facts.

## Desvios e decisões

- A superfície não ganhou tool, verbo ou chamada live. O analyzer Flink
  existente continua sendo a porta para o novo fact.
- `metrics` aceita lista, objeto único com nome e wrapper
  `metrics.observations`; nenhum timestamp numérico é convertido em epoch.
- Metadados aninhados não entram em `attrs`, evitando copiar estruturas sem
  contrato; metadados escalares não reservados são preservados.
- A regeneração golden revelou dois expected Managed Flink defasados no corpus;
  ambos foram atualizados pelo script oficial junto da fixture nova.
- T5 foi verificado com uma divergência controlada no espelho gerado (exit 1),
  seguida de regeneração oficial e o mesmo teste verde (exit 0).

## Revisão

Revisão local de especificação: T1 cobre AC1/AC6, T2 cobre ausência e tipo de
timestamp, T3 cobre shape/valor, T4 fecha o corpus e T5 fecha documentação e
superfícies geradas. Revisão local de qualidade: namespaces upstream e Managed
Flink permanecem separados; não há claim de saúde, SLO, causalidade, custo,
throughput ou ganho; o núcleo continua offline.

## Validação executada

- `tests/test_facts_flink.py` — **11 passed**.
- `tests/test_fixtures_golden_flink.py` — **7 passed**.
- `tests/test_fixtures_kind_coverage.py` — **69 passed**.
- `tests/test_reference_docs.py::test_referencia_em_dia` — **1 passed**.
- Gates de skills, referências, superfície, knowledge, reachability e bundle
  offline passaram; a suíte completa não foi executada.
