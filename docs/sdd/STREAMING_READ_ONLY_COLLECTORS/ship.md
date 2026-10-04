---
sdd: 1
feature: STREAMING_READ_ONLY_COLLECTORS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_READ_ONLY_COLLECTORS/build_report.md
  sha256: "2122c9b2a84098adaab409c997c3a49698fb6ce7a2e9c5f25157087717eb21c1"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, offline_manifest, sources_lock, status_numbers, status_numbers_gate, artifact_kind_registry, collector_tests, reachability_lists, fixture_kind_coverage, snippet_measure]
deviations: ["Connect/Streams/OpenLineage live e métricas temporais permanecem N/A + motivo; não existe endpoint AWS universal."]
---

# STREAMING_READ_ONLY_COLLECTORS — entrega

Collector read-only entregue para checkpoint S3, Glue Streaming, Kinesis, MSK e
DMS, com redaction, cache por hash, manifesto, CLI, MCP, testes e documentação.

## Gates rodados

- `python -m pytest tests/test_collect_streaming.py tests/test_collect_base.py tests/test_collect_aws.py -q --basetemp .sparkforge/local/pytest-streaming-collectors` — `84 passed`, exit 0.
- `python -m pytest tests/test_adapters_tools.py::TestOutputSchemasAreReal tests/test_host_surface_contracts.py -q --basetemp .sparkforge/local/pytest-streaming-collectors-surface` — `5 passed`, exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge sdd check --repo . --feature STREAMING_READ_ONLY_COLLECTORS` — `ok: true`.

## Lições

- Collector deve ser ponte de aquisição, não juiz: toda conclusão operacional
  continua no analyzer com facts, rules e unresolved.
- Redaction e cache por hash são controles independentes; cache não pode
  preservar segredo nem esconder mudança de artefato.
