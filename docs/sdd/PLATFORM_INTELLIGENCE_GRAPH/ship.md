---
sdd: 1
feature: PLATFORM_INTELLIGENCE_GRAPH
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_GRAPH/build_report.md
  sha256: "692b466556c363256fbf9cc070638cf0961c592312e00c57755e0fe97207929f"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, surface_lock, generated_reference]
deviations:
  - "T1–T3 não registraram red/green porque a implementação precede o build_report; o histórico não foi reescrito e nenhum exit vermelho foi inventado."
  - "A validação direcionada foi repetida com basetemp dentro do workspace porque o diretório TEMP padrão do host recusou criação por WinError 5."
---

# PLATFORM_INTELLIGENCE_GRAPH — entrega

## Hipótese

Confirmada no escopo offline. Um manifesto declarativo carregado em JSON ou YAML
produz fingerprint e ordenação estáveis; impacto downstream/upstream/both segue
somente arestas explícitas, com limite de profundidade/itens e unresolved para
endpoint, atributo ou nó ausente; CLI e MCP compartilham o mesmo contrato.

## O que foi entregue

- Contrato `contracts/platform-graph-v1.schema.json` e fixture sintético.
- Loader canônico JSON/YAML, entidades, arestas, evidência, proveniência,
  conflitos, fingerprint e impacto bounded.
- `analyze platform-graph` e `sparkforge_analyze_platform_graph` sobre o mesmo
  núcleo.
- Documentação, surface lock, parity e referências geradas.

## Gates rodados

- `python -m pytest tests/test_platform_graph.py -q --basetemp .sparkforge/local/pytest-platform-graph` — `4 passed`, exit 0.
- `python -m sparkforge_aws.adapters.cli analyze platform-graph --path fixtures/platform/graph.yaml --changed-node postgres.orders --direction downstream` — exit 0.
- `python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q --basetemp .sparkforge/local/pytest-platform-graph-gates` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge-aws sdd check --repo . --feature PLATFORM_INTELLIGENCE_GRAPH` — `ok: true`.

## Limites e rollback

Não há conectores AWS, Kafka, Flink, dbt ou catálogo ao vivo nesta feature; o
rollback é reverter os commits `22a6193`, `a2adb04` e `2ce0c4e` em ordem inversa,
mantendo os artefatos SDD para auditoria.

## Lições

- Contrato de grafo deve ser fechado antes de adicionar conectores, para impedir
  que cada integração crie semântica própria de lineage.
- Basetemp explícito deve ser padrão dos gates Windows deste repositório quando o
  TEMP do host não for gravável.
