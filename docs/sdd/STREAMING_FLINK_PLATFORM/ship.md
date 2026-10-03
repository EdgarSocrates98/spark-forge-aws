---
sdd: 1
feature: STREAMING_FLINK_PLATFORM
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_FLINK_PLATFORM/build_report.md
  sha256: "ea9ecb9175967b01422c620ccd37d1c68111865f09c9b67a672c05a029947e55"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, fixture_corpus_gates, offline_manifest, sources_lock, surface_lock, generated_reference, rules_catalog_gates, manifest_rule_count, routing_yaml, coordinator_rule_areas, router_gates, sync_skills, agents_parity, status_numbers_gate]
deviations:
  - "A skill canônica fica em skills/; .agents/skills/, .claude/skills/ e referências são espelhos gerados."
  - "A onda cobre análise offline de dumps Flink e Managed Flink; não adiciona collector live, matriz de versões, limiar de backpressure, custo ou garantia exactly-once."
  - "A integração de surface, manifesto, reachability, agentes, skills e contagens foi fechada após o build e validada pelo lote de 209 testes de integração."
---

# STREAMING_FLINK_PLATFORM — entrega

## Hipótese

Confirmada no escopo declarado: dumps JSON/JSONL de Apache Flink e Managed Flink
podem ser extraídos offline em namespaces separados, com ausência nomeada como
`unresolved`, julgados por regras ancoradas e expostos por CLI/MCP com o mesmo
envelope. Isso não prova capacidade produtiva, causalidade, custo, versão
compatível, exactly-once ou comportamento de uma aplicação não observada.

## Entrega

- extrator determinístico `sparkforge/facts/flink.py` para job, operator,
  checkpoint, state, aplicação Managed Flink, config, connector e metric;
- `sparkforge analyze flink` e `sparkforge_analyze_flink`, com seleção explícita
  de `flink` ou `managed_flink`;
- regras `SF-FLINK-001` para checkpoint falho e `SF-FLINK-002` para backpressure
  positivo observado, sem disparar por métrica ausente;
- corpus golden positivo, falha de checkpoint, backpressure e unresolved;
- skill `analyze-flink-job`, coordenador `streaming-realtime-architect`, rota,
  parity, manifesto, espelhos e referências geradas;
- conhecimento offline com fontes oficiais e hash no manifesto.

## Gates

| gate | comando/resumo | resultado |
|---|---|---|
| facts, goldens e superfície | `python -m pytest tests/test_facts_flink.py tests/test_fixtures_golden_flink.py tests/test_analyze_flink.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\flink-final` | 11 passed |
| integração de referências, cobertura e paridade | `python -m pytest tests/test_offline_expansion.py tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\flink-integration` | 209 passed |
| catálogo, fixtures e routing | suítes de reachability, kinds, router, capability/parity e adapters | pass nos lotes direcionados |
| espelhos | `python scripts/sync_skills.py --check` | exit 0 |
| surface | `python scripts/check_surface_lock.py` | exit 0; 0 divergências |
| conhecimento | `python scripts/verify_offline_bundle.py` | exit 0; 60 documentos |
| números correntes | `python scripts/check_status_numbers.py --strict` | exit 0; 0 divergências |
| SDD | `sparkforge sdd check --repo . --feature STREAMING_FLINK_PLATFORM` | `ok: true`; 0 recusas; 0 unresolved |

## Rollback

Reverter os commits desta onda na ordem inversa. Remover juntos extrator,
regras, fixtures, knowledge, locks, surface, referências, manifesto, parity,
skill, agente e routing; não executar collector live como parte do rollback.

## Pendências explícitas

Flink/Managed Flink ainda precisa de matriz de runtime compatível, coleta
read-only real versionada, métricas temporais, correlação de restart/source/sink,
regras de latência e validação funcional. As ondas Glue Streaming/RTM, CDC,
Schema Registry, contratos, Iceberg streaming, observabilidade e arquitetura
continuam pendentes na matriz de cobertura do prompt.

## Lições

Namespaces de serviço e upstream precisam permanecer separados. Métrica ausente
precisa gerar `unresolved`, não zero. Uma nova skill/coordenador também exige
atualizar reachability, fronteira destrutiva, manifesto, routing, paridade,
referências e contagens antes do commit.
