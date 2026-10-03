---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY_COLLECTOR
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY_COLLECTOR/build_report.md
  sha256: "8b36ffe9ff538ad2444c2c0b99151c323c55eb28f3c8958a40e4ce6cd04df212"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, generated_reference, surface_lock, reachability_lists, sync_skills, status_numbers_gate, requirements_mirror, hash_locks]
deviations:
  - "A coleta captura a versão latest observada por schema; histórico completo de versões, matriz regional completa, consumidores cross-artifact e validação funcional permanecem fora do feature."
  - "A suíte completa não foi executada; os gates focados e de distribuição foram executados."
---

# STREAMING_SCHEMA_REGISTRY_COLLECTOR — entrega

Entrega coletor read-only do AWS Glue Schema Registry, com paginação limitada,
metadata de registry/schema, latest schema version, definição opcional redigida,
`unresolved` nomeado, cache offline-first, manifesto SHA-256, CLI, MCP, parity,
knowledge e referências geradas.

## Hipótese

Confirmada: uma identidade declarada de registry/schema produz artefato
consumível por `analyze schema-registry`, preserva a versão latest observada e
não executa operações de criação, alteração ou exclusão no Glue. A mesma coleta
tem envelope equivalente na CLI e no MCP.

## Gates

- `python -m pytest tests/test_collect_schema_registry.py tests/test_adapters_tools.py::TestToolSurface tests/test_fixtures_golden_mcp_parity.py -q --basetemp=...` — `25 passed`.
- `python scripts/gen_reference_docs.py --check`.
- `python scripts/sync_skills.py --check`.
- `python scripts/check_surface_lock.py`.
- `python scripts/check_status_numbers.py --strict`.
- `python scripts/verify_offline_bundle.py --check`.
- `python scripts/refresh_knowledge.py --check --offline`.
- `sparkforge sdd check --repo . --feature STREAMING_SCHEMA_REGISTRY_COLLECTOR`.
- Suíte completa não executada; permanece para fase explicitamente solicitada.

## Limites

O coletor não grava no AWS Glue Schema Registry. Limites de schemas e bytes de
definição são explícitos; ausência, definição omitida ou formato não parseável
não vira contrato inventado. A entrega não prova compatibilidade runtime,
consumidores, latência, replay, custo, capacidade ou validação funcional.
