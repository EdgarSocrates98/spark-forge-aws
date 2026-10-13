---
sdd: 1
feature: STREAMING_ICEBERG_TEMPORAL
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_ICEBERG_TEMPORAL/build_report.md
  sha256: "915f96c2759554bca9c72c7d754eaf4e0269f83cdd3c3bd25fecdd6694468866"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, offline_manifest, sources_lock, status_numbers, status_numbers_gate, manifest_rule_count, reachability_lists, fixture_kind_coverage, fixture_corpus_gates, snippet_measure, rules_catalog_gates, runtime_scope_gate, wheel_gate, sync_skills, agents_parity, sdd_check]
deviations:
  - "O schema factual precisou aceitar subject.type=snapshot para validar facts granulares."
  - "Goldens Iceberg legados e observability foram regenerados para refletir o envelope atual, incluindo max_skew_seconds explícito no fact analisado."
  - "A primeira rodada do gate de catálogo encontrou manifest.rule_count=209; o valor foi atualizado para 210 e o gate completo terminou verde."
  - "O pytest usou basetemp explícito no Windows."
  - "A suíte completa não foi executada; o escopo desta fase foi validado pelos gates direcionados registrados."
---

# STREAMING_ICEBERG_TEMPORAL — entrega

## Hipótese

Confirmada no escopo offline: quando query, tabela, timestamps observados e
tolerância são declarados, SparkForge produz fatos granulares de snapshots,
pareia progresso e commits Iceberg de forma determinística, preserva evidência
de origem e mantém unresolved quando a janela não pode ser comparada. Uma
operação não-append observada gera recomendação de replay/validação sem
atribuição causal.

## Critérios de aceite

| critério | evidência | resultado |
|---|---|---|
| AC1 | tests/test_facts_iceberg_metadata.py::TestSnapshotsSummary::test_snapshot_observation_facts_preserve_identity_and_timestamp | verde |
| AC2–AC3 | tests/test_facts_streaming_composition.py | verde |
| AC4 | tests/test_streaming_rules.py::test_temporal_iceberg_rule_requires_pairs_and_non_append | verde |
| AC5 | tests/test_analyze_streaming_composition.py::test_iceberg_temporal_cli_and_mcp_envelopes_match | verde |
| AC6 | fixtures temporais e tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens | verde |
| AC7 | mirrors, referências, knowledge, coverage, surface, manifest e status | verde |

## Gates rodados

| registro | comando | resultado |
|---|---|---|
| foco da feature | tests/test_facts_iceberg_metadata.py tests/test_facts_streaming_composition.py tests/test_streaming_rules.py tests/test_analyze_streaming_composition.py tests/test_fixtures_golden_streaming_composition.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py tests/test_reference_docs.py tests/test_surface_lock.py | 980 passed |
| catálogo, docs, fixtures e knowledge | tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py | 1193 passed |
| runtime scope | tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py | 769 passed |
| wheel | tests/test_verify_wheel.py | 46 passed |
| snippet measure | tests/test_harness_untrusted.py | 4 passed |
| sources lock | python scripts/refresh_knowledge.py --update --offline; tests/test_refresh_knowledge.py | sincronizado; 39 passed |
| referências | python -m pytest tests/test_reference_docs.py -q | 5 passed |
| mirrors | python scripts/sync_skills.py --check | OK |
| referências geradas | python scripts/gen_reference_docs.py --check | OK |
| surface | python scripts/check_surface_lock.py | 0 divergências |
| bundle offline | python scripts/verify_offline_bundle.py --check --repo . | 69 checked, 0 failed |
| números correntes | python scripts/check_status_numbers.py --strict | 0 divergências |
| SDD | sparkforge-aws sdd check --repo . --feature STREAMING_ICEBERG_TEMPORAL | ok |

## Entregue

- iceberg.snapshot granular com identidade, operação e timestamp observado.
- mode=iceberg_temporal na CLI, MCP e core compartilhado.
- Pareamento temporal determinístico entre progresso e snapshots, com tolerância
  declarada, source_fact_ids e causal_inference=false.
- SF-STREAMICE-002 com finding evidence-first para non-append observado.
- Goldens append, non-append, unresolved e regressão do modo Iceberg legado.
- Schema factual, skill, agente, mirrors, knowledge, prompt coverage, referências,
  surface lock, offline manifest, manifesto de contagem e números correntes.
- SDD completo até ship.

## Limites remanescentes

- Não há collector live, replay funcional, benchmark cloud ou correlação de longo
  período com CloudWatch/Spark.
- Não há inferência de causalidade, SLO, FinOps, capacidade, exactly-once ou ganho.
- Timestamps dependem do dump observado; ausência permanece unresolved.
- FORGE_LAB_DIGITAL_TWIN e INTEGRACAO_USUARIO continuam nos estados SDD já
  registrados; este fechamento não altera esses escopos.
