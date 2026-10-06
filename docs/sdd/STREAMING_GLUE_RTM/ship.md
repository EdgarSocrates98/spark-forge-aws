---
sdd: 1
feature: STREAMING_GLUE_RTM
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_GLUE_RTM/build_report.md
  sha256: "a74b2ab57fa662126b56d959e49f44fcd2ddec050c19f58fcfe0e7e65df44461"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, fixture_corpus_gates, snippet_measure, offline_manifest, sources_lock, surface_lock, generated_reference, rules_catalog_gates, manifest_rule_count, routing_yaml, coordinator_rule_areas, router_gates, sync_skills, agents_parity, status_numbers_gate]
deviations:
  - "A wave cobre análise offline de dumps Glue Streaming/RTM; collector AWS, Terraform cross-artifact, matriz completa e validação funcional permanecem fora do escopo."
  - "A skill canônica fica em skills/; espelhos são gerados por scripts/sync_skills.py."
---

# STREAMING_GLUE_RTM — entrega

## Hipótese

Confirmada no escopo declarado: definições Glue Streaming/RTM salvas podem ser
extraídas, julgadas por facts ancorados e expostas por CLI/MCP sem converter
ausência em zero. Isso não prova o comportamento do job em produção.

## Pendências nomeadas

Terraform cross-artifact, collector read-only, matriz de versões, métricas
temporais e validação funcional continuam dependentes de ondas posteriores.

## Gates rodados

- `python -m pytest tests/test_facts_glue_streaming.py tests/test_glue_streaming_rules.py tests/test_fixtures_golden_glue_streaming.py tests/test_analyze_glue_streaming.py -q --basetemp .sparkforge/local/pytest-glue-streaming` — `10 passed`, exit 0.
- `python -m pytest tests/test_capability_parity.py tests/test_agents_parity.py tests/test_offline_expansion.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -q --basetemp .sparkforge/local/pytest-glue-streaming-gates` — `1018 passed`, exit 0.
- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge-aws sdd check --repo . --feature STREAMING_GLUE_RTM` — `ok: true`.

## Lições

- RTM deve preservar ausência de capacidade como unresolved, nunca zero ou
  incompatibilidade inferida.
- A superfície Glue Streaming precisa seguir o mesmo envelope de facts da wave
  CDC para permitir composição posterior sem misturar vocabulários.
