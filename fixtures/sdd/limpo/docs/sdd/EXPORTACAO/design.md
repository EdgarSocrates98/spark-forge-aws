---
sdd: 1
feature: EXPORTACAO
phase: design
profile: dev
status: done
upstream:
  path: docs/sdd/EXPORTACAO/define.md
  sha256: "0339b7c1e867d95e2e3b42bd2a78883e34bbab9457432a1079d9de8228c401c2"
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

# EXPORTACAO — desenho
