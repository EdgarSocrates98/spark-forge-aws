---
sdd: 1
feature: STREAMING_FLINK_TEMPORAL_METRICS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_FLINK_TEMPORAL_METRICS/build_report.md
  sha256: "f22fb30e44ceb23de449864f296cff16f148a74b4241479ac0b44e554f9bf494"
hypothesis_outcome: confirmed
registries: [fixture_corpus_gates, reachability_lists, fixture_kind_coverage, sync_skills, agents_parity, snippet_measure, offline_manifest, sources_lock, surface_lock, generated_reference, status_numbers_gate]
deviations:
  - "A superfície reutiliza sparkforge analyze flink --artifact flink; não foi criada tool ou collector novo."
  - "A suíte completa não foi executada; validação ficou restrita a testes focados, coleta de testes e gates do feature."
---

# STREAMING_FLINK_TEMPORAL_METRICS — entrega

## Hipótese

Confirmada no escopo declarado. O artifact upstream com observações explícitas
produz `flink.metric` somente para nome, valor numérico e timestamp textual;
metadados escalares são preservados, estruturas aninhadas são descartadas e
entradas inválidas produzem `flink.unresolved`. Artifacts antigos sem `metrics`
mantêm compatibilidade. Isso não é coleta live, série longa, saúde, SLO,
causalidade, throughput ou validação funcional.

## Gates rodados

- `python -m pytest tests/test_facts_flink.py -q --basetemp .pytest-flink-temporal-regression` — **11 passed**.
- `python -m pytest tests/test_fixtures_golden_flink.py -q --basetemp .pytest-flink-temporal-t4-green` — **7 passed**.
- `python -m pytest tests/test_fixtures_kind_coverage.py -q --basetemp .pytest-flink-temporal-kind` — **69 passed**.
- `python -m pytest tests/test_reference_docs.py::test_referencia_em_dia -q --basetemp .pytest-flink-temporal-t5-green` — **1 passed**.
- `python -m pytest tests/test_reference_docs.py tests/test_sync_render.py tests/test_agents_parity.py tests/test_docs_coverage.py tests/test_status_numbers_gate.py tests/test_refresh_knowledge.py tests/test_offline_expansion.py -q --basetemp .pytest-flink-temporal-final-docs2` — **335 passed**.
- `python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q --basetemp .pytest-flink-temporal-final-reach2` — **946 passed**.
- `python -m pytest tests/ --collect-only -q -p no:cacheprovider` — **14496 testes coletados**.
- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0, 0 divergências.
- `python scripts/check_status_numbers.py --strict` — exit 0, 0 divergências.
- `python scripts/refresh_knowledge.py --check --offline` — exit 0, 340 fontes.
- `python scripts/verify_offline_bundle.py --check` — exit 0, 69/69.
- `sparkforge sdd check --repo . --feature STREAMING_FLINK_TEMPORAL_METRICS` — exit 0.
- `git diff --check` — exit 0.

## Limites

O ship cobre contrato de artifact offline, aliases de campos, preservação
fail-closed, facts, fixture golden, analyzer existente, skill, knowledge,
mirrors, referências e contadores. Não cobre REST Flink live, job graph,
savepoints, runtime observado regional, série longa, replay, benchmark,
validação funcional, health/SLO, causalidade, custo ou escrita AWS.
