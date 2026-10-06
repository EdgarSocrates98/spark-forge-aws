---
sdd: 1
feature: STREAMING_CDC
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_CDC/build_report.md
  sha256: "39e7cd589eb7cd6ce1483cab456107d552fe77bd06db285ce870d0ee8c2228d7"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, fixture_corpus_gates, snippet_measure, offline_manifest, sources_lock, surface_lock, generated_reference, rules_catalog_gates, manifest_rule_count, routing_yaml, coordinator_rule_areas, router_gates, sync_skills, agents_parity, status_numbers_gate]
deviations:
  - "A wave cobre análise offline de eventos CDC, Debezium e DMS; collectors, matriz de versões, Schema Registry e validação funcional permanecem em waves posteriores."
  - "A skill canônica fica em skills/; espelhos e referências são gerados pelos scripts do repositório."
  - "A suíte ampla encontrou três links relativos quebrados nos guias Forge Lab; os links foram corrigidos para `docs/knowledge/` e a validação focada posterior passou."
---

# STREAMING_CDC — entrega

## Hipótese

Confirmada no escopo declarado: dumps CDC, Debezium e DMS podem ser extraídos,
julgados por facts ancorados e expostos por CLI/MCP sem preencher lacunas.
Isso não prova comportamento produtivo nem fecha o prompt inteiro.

## Pendências nomeadas

Collectors live, matriz de runtimes/conectores, Schema Registry, correlação
cross-artifact e validação funcional continuam dependentes das próximas waves.

## Gates rodados

- `python -m pytest tests/test_facts_cdc.py tests/test_cdc_rules.py tests/test_fixtures_golden_cdc.py tests/test_analyze_cdc.py tests/test_reference_docs.py -q --basetemp .sparkforge/local/pytest-streaming-cdc-final` — `21 passed`, exit 0.
- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge-aws sdd check --repo . --feature STREAMING_CDC` — `ok: true`.

## Lições

- Corpus CDC precisa cobrir ausência de posição, chave, tombstone e snapshot/CDC
  seam sem transformar lacuna em default operacional.
- Gates de referências devem acompanhar mudanças documentais de outras waves;
  links relativos precisam ser validados antes de declarar uma entrega pronta.
