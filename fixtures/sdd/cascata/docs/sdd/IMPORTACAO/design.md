---
sdd: 1
feature: IMPORTACAO
phase: design
profile: dev
status: done
upstream:
  path: docs/sdd/IMPORTACAO/define.md
  sha256: "6d685b9010dac6c369919f39fbb37754668143e789b16561f6100ba11ab89f52"
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

# IMPORTACAO — desenho
