---
sdd: 1
feature: SKILLS_QUALITY_EVOLUTION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SKILLS_QUALITY_EVOLUTION/design.md
  sha256: "5c0c462e1ffd3eaf2679c5a3f245a3a23e1ee23a6c1d49272dd0152e3300ba3b"
tasks:
  - id: T1
    files: [skills/_shared, scripts/upgrade_skills.py, scripts/audit_skills.py]
    covers: [AC1]
    test: {path: tests/test_skill_quality.py, name: test_all_source_skills_follow_contract}
  - id: T2
    files: [scripts/check_skill_evals.py, scripts/run_skill_evals.py, evals/skills, tests/test_skill_quality.py]
    covers: [AC2, AC3]
    test: {path: tests/test_skill_quality.py, name: test_offline_eval_runner_is_complete_and_has_no_provider_side_effect}
  - id: T3
    files: [skills]
    covers: [AC1]
    test: {path: tests/test_skill_quality.py, name: test_all_source_skills_have_skill_creator_evals}
  - id: T4
    files: [.claude/skills, .agents/skills, docs/guia/referencia/skills]
    covers: [AC4, AC5]
    test: {path: tests/test_skill_content.py, name: test_copias_conferem_com_a_renderizacao}
  - id: T5
    files: [docs/skills, docs/surface.lock.json, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC5]
    test: {path: tests/test_skill_quality.py, name: test_all_source_skills_follow_contract}
  - id: T6
    files: [tests/test_skill_quality.py]
    covers: [AC6]
    test: {path: tests/test_skill_quality.py, name: test_offline_eval_runner_is_complete_and_has_no_provider_side_effect}
---

# SKILLS_QUALITY_EVOLUTION — plano

Cada tarefa preserva `skills/` como fonte, gera espelhos depois da edição e
registra comando, saída e contagem no build report. O lote final roda
sequencialmente porque os goldens compartilham estado de fixtures; resultados
parciais não fecham a hipótese.
