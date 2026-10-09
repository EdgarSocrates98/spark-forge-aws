---
sdd: 1
feature: JOB_VENDAS
phase: design
profile: operator
status: done
upstream:
  path: docs/sdd/JOB_VENDAS/define.md
  sha256: "2b8b464e112eaf6699e90a52dd90ce9dbac58a6cbd02207ecccd65788b7ef2ac"
files:
- path: src/modulo.txt
  action: modify
  reason: ajuste sintetico
- path: src/novo.txt
  action: create
  reason: arquivo sintetico
decisions:
- id: D1
  choice: Mudar so o modulo.
  rejected: []
  rollback: git revert do commit.
covers:
- part: modulo
  acceptance:
  - AC1
---

# JOB_VENDAS — desenho
