---
sdd: 1
feature: STREAMING_CDC
phase: ship
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_CDC/build_report.md
  sha256: "0b51abc5d1a885e8fe6e891ce5545b5ab744e85db03213fd120ae3f004a9274f"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, fixture_corpus_gates, snippet_measure, offline_manifest, sources_lock, surface_lock, generated_reference, rules_catalog_gates, manifest_rule_count, routing_yaml, coordinator_rule_areas, router_gates, sync_skills, agents_parity, status_numbers_gate]
deviations:
  - "A wave cobre análise offline de eventos CDC, Debezium e DMS; collectors, matriz de versões, Schema Registry e validação funcional permanecem em waves posteriores."
  - "A skill canônica fica em skills/; espelhos e referências são gerados pelos scripts do repositório."
---

# STREAMING_CDC — entrega

## Hipótese

Confirmada no escopo declarado: dumps CDC, Debezium e DMS podem ser extraídos,
julgados por facts ancorados e expostos por CLI/MCP sem preencher lacunas.
Isso não prova comportamento produtivo nem fecha o prompt inteiro.

## Pendências nomeadas

Collectors live, matriz de runtimes/conectores, Schema Registry, correlação
cross-artifact e validação funcional continuam dependentes das próximas waves.
