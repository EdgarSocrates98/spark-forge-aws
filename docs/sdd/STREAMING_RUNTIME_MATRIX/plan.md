---
sdd: 1
feature: STREAMING_RUNTIME_MATRIX
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_RUNTIME_MATRIX/design.md
  sha256: "a8492dd4c21da6efe310a53f3aae09f1936433516b143226ffc730f8962228bf"
tasks:
  - {id: T1, files: [knowledge/streaming/runtime-matrix.md, knowledge/INDEX.md, docs/streaming/prompt-coverage.md], covers: [AC1], test: {path: tests/test_streaming_runtime_matrix.py, name: test_streaming_runtime_matrix_has_explicit_states_and_boundaries}}
  - {id: T2, files: [knowledge/sources.lock.json, knowledge/offline-manifest.json, tests/test_streaming_runtime_matrix.py], covers: [AC2, AC3], test: {path: tests/test_streaming_runtime_matrix.py, name: test_every_streaming_matrix_source_is_in_the_offline_source_lock}}
---

# STREAMING_RUNTIME_MATRIX — plano

Adicionar a matriz e seus limites; atualizar índice, source lock, offline
manifest e cobertura; executar teste dedicado e gates offline.
