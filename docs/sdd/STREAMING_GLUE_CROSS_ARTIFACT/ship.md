---
sdd: 1
feature: STREAMING_GLUE_CROSS_ARTIFACT
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_GLUE_CROSS_ARTIFACT/build_report.md
  sha256: "c25bd3cc793e15e85182b74816b1a8a848aa89290ad97f14cba8c906fa4cc69a"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, generated_reference, surface_lock, fixture_corpus_gates, fixture_kind_coverage, snippet_measure, reachability_lists, status_numbers_gate, rules_catalog_gates, manifest_rule_count, sync_skills, agents_parity]
deviations:
  - "Nenhuma ferramenta CLI/MCP nova: fuse existente foi reutilizado para conter superfície e payload."
  - "Collector live, Terraform state/interpolation, execução, capacidade, custo e validação funcional permanecem fora do contrato offline."
---

# STREAMING_GLUE_CROSS_ARTIFACT — entrega

Entrega facts, composição, regras, fixtures, goldens, conhecimento e skill para
comparar configuração efetiva de Glue Streaming com Terraform. O resultado
distingue drift de evidência insuficiente e preserva a cadeia de facts.

## Gates

- `python -m pytest --basetemp .pytest-tmp/glue-cross tests/test_streaming_glue_cross_artifact.py tests/test_fixtures_golden_streaming_glue_cross_artifact.py tests/test_fixtures_kind_coverage.py::test_every_fixture_domain_has_a_golden_module -q` — `12 passed`.
- `python -m pytest --basetemp .pytest-tmp/glue-gates tests/test_facts_fusion.py tests/test_rules_catalog_reachability.py -q` — `894 passed`.
- `python -m pytest --basetemp .pytest-tmp/docs-glue tests/test_docs_coverage.py::test_streaming_glue_cross_artifact_coverage tests/test_sync_render.py tests/test_agents_parity.py -q` — `156 passed`.
- `python scripts/gen_reference_docs.py --check`.
- `python scripts/sync_skills.py --check`.
- `python scripts/check_surface_lock.py`.
- `python scripts/verify_offline_bundle.py --check`.
- `python scripts/check_status_numbers.py --strict`.
- `sparkforge-aws sdd check --repo . --feature STREAMING_GLUE_CROSS_ARTIFACT`.
- Suíte completa não executada; permanece para a próxima fase solicitada.

## Limites

O vínculo exige `aws_glue_job.name` literal único. Não resolve Terraform
interpolado, não consulta AWS e não prova que a configuração está aplicada ou
que o job atende SLO, custo, capacidade ou semântica funcional.
