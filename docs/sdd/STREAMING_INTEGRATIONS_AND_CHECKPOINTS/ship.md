---
sdd: 1
feature: STREAMING_INTEGRATIONS_AND_CHECKPOINTS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_INTEGRATIONS_AND_CHECKPOINTS/build_report.md
  sha256: "fb556f9175621e2e31cc94d49f10990df44c0c248569fd24f52c4474e7260923"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, generated_reference, surface_lock, fixture_corpus_gates, fixture_kind_coverage, snippet_measure, reachability_lists, status_numbers_gate, rules_catalog_gates, manifest_rule_count]
deviations: ["collector live, replay temporal e benchmark são N/A + motivo por offline guarantee e ausência de endpoint/credencial"]
---

# STREAMING_INTEGRATIONS_AND_CHECKPOINTS — entrega

Entrega facts/rules/fixtures/analyzer e knowledge para checkpoint, Kafka Connect,
Kafka Streams e OpenLineage. Não afirma saúde live, exactly-once end-to-end ou
lineage completo sem evidência correspondente.

## Gates rodados

- `python -m pytest tests/test_streaming_integrations.py tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q --basetemp .sparkforge/local/pytest-streaming-integrations-gates` — `904 passed`, exit 0.
- `python -m pytest tests/test_capability_parity.py tests/test_host_surface_contracts.py -q --basetemp .sparkforge/local/pytest-streaming-integrations-surface` — `46 passed`, exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge sdd check --repo . --feature STREAMING_INTEGRATIONS_AND_CHECKPOINTS` — `ok: true`.

## Lições

- Checkpoint, Connect, Streams e OpenLineage precisam manter vocabulários
  separados dentro do envelope comum para evitar conclusões indevidas.
- Uma série curta não sustenta tendência; o contrato deve preservar a amostra
  e emitir unresolved até haver janela suficiente.
