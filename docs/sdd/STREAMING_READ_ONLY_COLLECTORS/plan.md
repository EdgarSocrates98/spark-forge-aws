---
sdd: 1
feature: STREAMING_READ_ONLY_COLLECTORS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_READ_ONLY_COLLECTORS/design.md
  sha256: "6ac1c2b94859ba54a076b4e46a41a5705f11de82bda7010b2d9949dffa0f5b4f"
tasks:
  - {id: T1, files: [sparkforge/collect/base.py, sparkforge/collect/streaming.py], covers: [AC1, AC2, AC3], test: {path: tests/test_collect_streaming.py, name: test_collector_composes_read_only_snapshots_and_redacts}}
  - {id: T2, files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py], covers: [AC4], test: {path: tests/test_collect_streaming.py, name: test_cli_parser_and_handler_are_wired}}
  - {id: T3, files: [tests/test_collect_streaming.py, knowledge/streaming-integrations.md], covers: [AC1, AC2, AC3], test: {path: tests/test_collect_streaming.py, name: test_offline_hit_does_not_touch_aws}}
  - {id: T4, files: [manifest.json, parity.yaml, docs/surface.lock.json, knowledge/offline-manifest.json], covers: [AC5], test: {path: tests/test_host_surface_contracts.py, name: test_full_and_compact_surfaces_have_declared_sizes}}
---

# STREAMING_READ_ONLY_COLLECTORS — plano

Implementar T1 antes da superfície; executar T2 após o contrato; fechar T3/T4
somente depois de regenerar artefatos derivados e medir os counts.
