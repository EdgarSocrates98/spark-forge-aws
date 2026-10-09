---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY/build_report.md
  sha256: "70e894441aaac68fa2f3695e050cd77a8661adfad45ebad7bc1a8b0ad7cfe0f1"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, fixture_corpus_gates, snippet_measure, offline_manifest, sources_lock, surface_lock, generated_reference, rules_catalog_gates, manifest_rule_count, routing_yaml, coordinator_rule_areas, agents_parity, sync_skills, status_numbers_gate]
deviations:
  - "Compatibilidade é proxy estrutural offline; registry remoto, consumidores vivos e mutação ficam fora do escopo."
---

# STREAMING_SCHEMA_REGISTRY — entrega

O domínio está diagnosticável no escopo offline. A matriz de streaming continua
aberta para cross-artifact, observabilidade e validação funcional.

## Gates rodados

- `python -m pytest tests/test_facts_schema_registry.py tests/test_schema_registry_rules.py tests/test_fixtures_golden_schema_registry.py tests/test_analyze_schema_registry.py -q --basetemp .sparkforge_aws/local/pytest-schema-registry` — `11 passed`, exit 0.
- `python -m sparkforge_aws.adapters.cli analyze schema-registry --path fixtures/schema_registry/schema_compatible/input/contract.json --limit 4` — exit 0.
- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge-aws sdd check --repo . --feature STREAMING_SCHEMA_REGISTRY` — `ok: true`.

## Lições

- Compatibilidade de schema deve ser proxy estrutural e declarada; não prova
  que consumidores vivos aceitarão a mudança.
- Auto-registro e política ausente são dimensões separadas de evolução e devem
  continuar explicitamente unresolved quando não observadas.
