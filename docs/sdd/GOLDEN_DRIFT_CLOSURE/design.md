---
sdd: 1
feature: GOLDEN_DRIFT_CLOSURE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/GOLDEN_DRIFT_CLOSURE/define.md
  sha256: "00e19f5d5d4ba4510b2c9f2fb3af1dd9839ceec8bdbbe3869d276b9bd1569acf"
files:
  - {path: fixtures/streaming_glue_cross_artifact, action: modify, reason: "Atualizar facts/findings dos três casos pelo regenerador oficial."}
  - {path: fixtures/scan/misto, action: modify, reason: "Atualizar summary derivado do scan atual."}
  - {path: fixtures/scenarios, action: modify, reason: "Atualizar assessment dos três pares de migração."}
  - {path: scripts/regen_streaming_glue_cross_artifact.py, action: modify, reason: "Usar script existente sem alterar sua implementação."}
  - {path: scripts/regen_fixtures.py, action: modify, reason: "Usar regenerador existente para os três cenários."}
decisions:
  - id: D1
    choice: "Regenerar somente casos falhos e preservar todos os findings/assessment produzidos pelos runners."
    rejected: ["Editar saídas manualmente", "Relaxar asserts", "Regenerar corpus inteiro"]
    rollback: "git revert do commit desta feature."
covers:
  - {part: "Glue cross-artifact", acceptance: [AC1]}
  - {part: "scan misto", acceptance: [AC2]}
  - {part: "migration scenarios", acceptance: [AC3]}
---

# GOLDEN_DRIFT_CLOSURE — desenho

Cada task chama a mesma implementação usada no teste/CLI. O regenerador é
instrumento de derivação, não novo comportamento.
