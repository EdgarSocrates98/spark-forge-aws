---
sdd: 1
feature: STREAMING_END_TO_END_PIPELINE
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_END_TO_END_PIPELINE/build_report.md
  sha256: "6a5391319b85461f8d70144af206fb68be1b5515291b8a1291e630ae96bc2464"
hypothesis_outcome: confirmed
registries: [rules_catalog_gates, manifest_rule_count, fixture_kind_coverage, reachability_lists, fixture_corpus_gates, docs_coverage, sync_skills, generated_reference, surface_lock, status_numbers_gate, snippet_measure, verify_wheel, runtime_scope_gates, offline_manifest, sources_lock, agents_parity, sdd_check]
deviations:
  - "A integração core/CLI/MCP foi implementada junto da composição; AC4 usa guard contra red artificial e mantém teste dedicado de paridade."
  - "O corpus revelou colisão de Fact.id entre nodes/edges com subject não específico; subjects determinísticos por identidade foram adicionados antes da regeneração dos goldens."
  - "A suíte completa não foi executada; validação ficou em gates focados da feature e registries afetadas."
  - "verify_wheel construiu dois artefatos byte-identical, mas a paridade instalada terminou com 47 falhas de goldens anteriores ao pipeline; o subset no checkout reproduziu exatamente o mesmo drift e nenhum golden fora do escopo foi regenerado."
---

# STREAMING_END_TO_END_PIPELINE — entrega

## Hipótese

Confirmada no escopo declarado. Um contrato versionado com selectors exatos
produz correspondência verificável de nodes e edges somente quando os facts
fornecidos sustentam identidade única. Ausência, ambiguidade ou shape inválido
permanece unresolved; nenhum vínculo é inferido por ordem, substring ou
coexistência de artefatos.

## Entrega

- `build_streaming_pipeline` produz `streaming.pipeline.node`,
  `streaming.pipeline.link`, `streaming.pipeline` e
  `streaming.pipeline.unresolved`, preservando provenance e `source_fact_ids`.
- `mode=pipeline` reutiliza `sparkforge-aws analyze streaming-composition` no core,
  CLI e MCP, com `--pipeline-path`/`pipeline_path`, paginação e detail level.
- `SF-STREAM-015` julga somente blind spot observado.
- Goldens cobrem completo, selector ausente, selector ambíguo e contrato inválido;
  scripts regeneram facts/findings de inputs commitados.
- Knowledge, skill, coordenador, guias, referências geradas, mirrors e números
  correntes descrevem o contrato e seus limites.

## Gates rodados

- `python -m pytest tests/test_streaming_pipeline.py tests/test_fixtures_golden_streaming_pipeline.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-registry` — **967 passed**.
- `python -m pytest tests/test_docs_coverage.py::test_manifest_counts_match_measurements tests/test_docs_coverage.py::test_streaming_coverage_mentions_slo_evaluation tests/test_docs_coverage.py::test_streaming_transport_slo_coverage_mentions_transport_key -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-t5-green` — **3 passed**.
- `python scripts/check_status_numbers.py --strict` — exit 0; zero divergências.
- `sparkforge-aws sdd check --repo . --feature STREAMING_END_TO_END_PIPELINE` — exit 0.
- `python scripts/sync_skills.py` — mirrors regenerados.
- `python scripts/gen_reference_docs.py` — referências regeneradas.
- `python -m pytest tests/test_harness_untrusted.py -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-snippet3` — **4 passed** em 155,57s.
- `python -m pytest tests/test_rule_scope_by_nature.py tests/test_rules_version_scope.py tests/test_runtime_glue_versions.py tests/test_runtime_inferred_from_facts.py -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-runtime2` — **823 passed** em 212,02s.
- `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-agents2` — **186 passed** em 23,90s.
- `python scripts/verify_offline_bundle.py` — **70 checked**, `failed: []`.
- `python scripts/refresh_knowledge.py --check --offline` — **341 fontes**, lock em dia.
- `python scripts/check_surface_lock.py` — **0 divergência(s)**.
- `python scripts/sync_skills.py --check` — mirrors em dia.
- `python scripts/gen_reference_docs.py --check` — referências em dia.
- `python scripts/check_status_numbers.py --strict` — **0 divergência(s)**.
- `python scripts/verify_wheel.py` — builds byte-identical; paridade instalada com `TEMP/TMP` isolados terminou **47 failed, 3467 passed, 5 skipped** em 1:06:06. O primeiro intento foi bloqueado por `WinError 5` no temp global; subset local reproduziu as mesmas falhas fora do escopo.

## Limites

O ship cobre composição declarativa offline, regra, goldens, cobertura de kinds,
paridade de portas, knowledge, skills, agents, mirrors, referências, contadores
e SDD. Não cobre descoberta automática de topologia, collectors live,
latência, throughput, disponibilidade, backlog, custo, causalidade,
exactly-once, saúde, replay, benchmark ou validação funcional.
