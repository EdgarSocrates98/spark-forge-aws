---
sdd: 1
feature: STREAMING_ARCHITECTURE_DECISION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_ARCHITECTURE_DECISION/design.md
  sha256: "88929a0cd8f8d7d7de267f2c03d68f138bc2ea424770d49b4ce40288a9028e88"
tasks:
  - {id: T1, files: [sparkforge/architecture/streaming.py, tests/test_streaming_architecture.py], covers: [AC1, AC2, AC3], test: {path: tests/test_streaming_architecture.py, name: test_candidate_matrix_refuses_underdetermined_winner}}
  - {id: T2, files: [fixtures/realtime_architecture, tests/test_streaming_architecture.py], covers: [AC1, AC3], test: {path: tests/test_streaming_architecture.py, name: test_fixture_results_are_stable_and_requirements_stay_separate}}
  - {id: T3, files: [sparkforge/adapters/cli.py, tests/test_streaming_architecture.py], covers: [AC4], test: {path: tests/test_streaming_architecture.py, name: test_cli_emits_adr_and_matrix}}
  - {id: T4, files: [knowledge/streaming-realtime-candidate-matrix.md, skills/design-realtime-data-architecture/SKILL.md, agents/streaming-realtime-architect.md, docs/streaming/prompt-coverage.md], covers: [AC5], test: {path: tests/test_streaming_architecture.py, name: test_fixture_results_are_stable_and_requirements_stay_separate}}
---

# STREAMING_ARCHITECTURE_DECISION — plano

Implementar o engine e fixtures antes da skill; validar o comando; regenerar
mirrors/referências; fechar SDD e só então commitá-lo.
