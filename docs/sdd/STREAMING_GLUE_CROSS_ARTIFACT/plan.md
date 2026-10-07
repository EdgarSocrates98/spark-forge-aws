---
sdd: 1
feature: STREAMING_GLUE_CROSS_ARTIFACT
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_CROSS_ARTIFACT/design.md
  sha256: "d790a6dcf9da0690b1ed96bd4b69383bcb537546ca431c0942aa5ee23517382a"
tasks:
  - id: T1
    files: [sparkforge_aws/facts/streaming_glue_cross.py, tests/test_streaming_glue_cross_artifact.py]
    covers: [AC1, AC2]
    test: {path: tests/test_streaming_glue_cross_artifact.py, name: test_matches_effective_glue_job_to_terraform_resource}
  - id: T2
    files: [sparkforge_aws/facts/fusion.py, tests/test_streaming_glue_cross_artifact.py]
    covers: [AC4]
    test: {path: tests/test_streaming_glue_cross_artifact.py, name: test_fuse_cross_artifact_is_guarded_and_idempotent}
  - id: T3
    files: [rules/catalog/glue-streaming.yaml, tests/test_streaming_glue_cross_artifact.py]
    covers: [AC3]
    test: {path: tests/test_streaming_glue_cross_artifact.py, name: test_cross_artifact_rules_are_evidence_backed}
  - id: T4
    files: [fixtures/streaming_glue_cross_artifact, scripts/regen_streaming_glue_cross_artifact.py, tests/test_streaming_glue_cross_artifact.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_streaming_glue_cross_artifact.py, name: test_fixture_goldens_cover_match_drift_and_unresolved}
  - id: T5
    files: [knowledge/glue-streaming-rtm.md, skills/review-glue-streaming/SKILL.md, docs/streaming/prompt-coverage.md]
    covers: [AC5]
    test: {path: tests/test_docs_coverage.py, name: test_streaming_glue_cross_artifact_coverage}
---

# STREAMING_GLUE_CROSS_ARTIFACT — plano

Implementação serializada: primeiro contrato/facts e testes vermelhos, depois
fuse, regras e goldens; por fim skill, knowledge, cobertura do prompt e gates
derivados. Nenhum novo verbo entra na superfície nesta wave.
