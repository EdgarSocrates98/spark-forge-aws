---
sdd: 1
feature: STREAMING_TEMPORAL_EVIDENCE
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_TEMPORAL_EVIDENCE/build_report.md
  sha256: "987857a7008d39d271dea4f24358b1f03163c77a00a639c9fa4aa1d9e1fd9fd5"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, offline_manifest, status_numbers, reachability_lists, fixture_kind_coverage, snippet_measure, fixture_corpus_gates, sources_lock, rules_catalog_gates, manifest_rule_count, sync_skills, agents_parity, status_numbers_gate]
deviations:
  - "O gate de corpus exigiu goldens persistidos em expected/; facts.json e findings.json foram adicionados para Kafka, Kinesis e missing_timestamp."
  - "A primeira rodada documental encontrou rule_count 208 desatualizado; manifest, README, guias e STATUS foram remediados para 209."
  - "O pytest global usou basetemp explícito por permissão negada no diretório temporário padrão do Windows."
  - "A suíte completa não foi executada, conforme pedido explícito para esta fase; apenas gates direcionados foram rodados."
---

# STREAMING_TEMPORAL_EVIDENCE — entrega

## Hipótese

Confirmada no escopo offline: quando query, transporte, timestamps e tolerância
de skew são declarados, o Spark Forge consegue compor observações temporais
pareadas, manter os ids de origem e julgar um finding evidence-first. Quando
qualquer elo falta, o resultado é unresolved, não ausência silenciosa nem causa
inferida.

## Critérios de aceite

| critério | evidência | resultado |
|---|---|---|
| AC1–AC2 | `tests/test_facts_streaming_temporal.py` | verde |
| AC3 | `tests/test_facts_transport.py::test_transport_preserves_observed_timestamp` | verde |
| AC4 | `tests/test_streaming_rules.py::test_temporal_rule_requires_paired_observations` | verde |
| AC5 | `fixtures/streaming_temporal/*/expected` e `tests/test_fixtures_golden_streaming_temporal.py` | verde |
| AC6 | `tests/test_analyze_streaming_composition.py::test_temporal_cli_and_mcp_envelopes_match` | verde |
| AC7 | mirrors, knowledge, referências, surface lock, offline manifest e gates abaixo | verde |

## Gates rodados

| registro | comando | resultado |
|---|---|---|
| catálogo, docs, fixtures e knowledge | `python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py -q` | 1188 passed |
| runtime scope | `python -m pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q` | 766 passed |
| temporal core | `python -m pytest tests/test_facts_streaming_temporal.py tests/test_facts_transport.py tests/test_streaming_rules.py tests/test_fixtures_golden_streaming_temporal.py tests/test_facts_streaming_composition.py tests/test_analyze_streaming_composition.py -q` | 17 passed |
| referências | `python -m pytest tests/test_reference_docs.py -q` | 5 passed |
| wheel/corpus | `python -m pytest tests/test_verify_wheel.py -q` | 46 passed |
| mirrors | `python scripts/sync_skills.py --check` | OK |
| referências geradas | `python scripts/gen_reference_docs.py --check` | OK |
| surface | `python scripts/check_surface_lock.py` | 0 divergências |
| bundle offline | `python scripts/verify_offline_bundle.py --check --repo .` | 69 checked, 0 failed |
| números correntes | `python scripts/check_status_numbers.py --strict` | 0 divergências |

## Entregue

- `analyze streaming-composition --mode temporal` na CLI e em
  `sparkforge_analyze_streaming_composition`.
- Extrator puro `streaming_temporal` com pairing determinístico, skew observado,
  `source_fact_ids`, janela incompleta e razões unresolved.
- Preservação de timestamps Kafka/Kinesis já presentes no dump.
- Regra `SF-STREAMOBS-002`, com dois pares mínimos e sem limiar inventado.
- Goldens positivos e negativos com cobertura de kinds, regra e ramo de severidade.
- Skill, mirrors, knowledge, prompt coverage, referências geradas, surface lock,
  offline manifest, README, guias, STATUS e ledger SDD atualizados.

## Limites remanescentes

- Não há collector live nem correlação de longo período com CloudWatch/Spark.
- Não há inferência de causalidade, SLO, custo, capacidade, exactly-once ou ganho.
- Os timestamps continuam dependentes do artefato observado; relógio local e ordem
  de arquivo não são substitutos.
- Reexecução da suíte completa fica para a próxima fase solicitada pelo usuário.
