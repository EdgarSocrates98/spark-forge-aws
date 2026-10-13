---
sdd: 1
feature: GOLDEN_DRIFT_CLOSURE
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/GOLDEN_DRIFT_CLOSURE/design.md
  sha256: "77c708eff3c178fa851c21a89421037250d3cb64ddbc3a676c1ac11625a0f1db"
tasks:
  - id: T1
    files: [fixtures/streaming_glue_cross_artifact, scripts/regen_streaming_glue_cross_artifact.py]
    covers: [AC1]
    test: {path: tests/test_fixtures_golden_streaming_glue_cross_artifact.py, name: "test_streaming_glue_cross_artifact_golden"}
  - id: T2
    files: [fixtures/scan/misto, tests/test_fixtures_golden_scan.py]
    covers: [AC2]
    test: {path: tests/test_fixtures_golden_scan.py, name: "test_golden[misto]"}
  - id: T3
    files: [fixtures/scenarios, scripts/regen_fixtures.py]
    covers: [AC3]
    test: {path: tests/test_fixtures_scenarios.py, name: "TestGolden::test_assessment_matches_golden"}
---

# GOLDEN_DRIFT_CLOSURE — plano

1. Rodar cada node vermelho e registrar o drift.
2. Regenerar somente os casos enumerados pelos scripts oficiais.
3. Revisar diff; não aceitar alteração manual de finding/assessment.
4. Rodar cada módulo completo e o gate comum de corpus.

Commit: `test(fixtures): close residual golden drift`
