---
sdd: 1
feature: STREAMING_STRUCTURED_REVIEW
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_STRUCTURED_REVIEW/design.md
  sha256: "11c3ec30ce7f5201ca18c5fae624ef15c46afa0f20d8dd43ae8986dbf7cbe795"
tasks:
  - {id: T1, files: [skills/review-structured-streaming/SKILL.md, skills/review-structured-streaming/evals/evals.json, skills/review-structured-streaming/references/README.md, skills/review-structured-streaming/scripts/validate_evidence.py], covers: [AC1, AC2], test: {path: tests/test_skill_quality.py, name: test_all_source_skills_follow_contract}}
  - {id: T2, files: [agents/streaming-realtime-architect.md, sparkforge/integrate/render.py, tests/test_sync_render.py], covers: [AC3], test: {path: tests/test_sync_render.py, name: TestSkillsReais::test_agent_so_aparece_onde_ha_um_coordenador_so}}
  - {id: T3, files: [README.md, docs/guia/05-agents-e-skills.md, docs/guia/12-espelhos-e-dependencias.md, docs/superpowers/STATUS.md], covers: [AC4], test: {path: tests/test_docs_coverage.py, name: TestManifest::test_skills_list_equals_the_skills_on_disk}}
  - {id: T4, files: [docs/surface.lock.json, docs/guia/referencia/skills/], covers: [AC3, AC4], test: {path: tests/test_sync_render.py, name: TestSkillsReais::test_render_e_idempotente}}
---

# STREAMING_STRUCTURED_REVIEW — plano

Implementar skill e eval antes dos espelhos; registrar dispatch e coordenador;
regenerar documentação e counts; executar auditoria, evals, mirrors, SDD e
regressão focada.
