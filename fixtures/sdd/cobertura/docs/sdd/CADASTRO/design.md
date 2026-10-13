---
sdd: 1
feature: CADASTRO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/CADASTRO/define.md
  sha256: "8d3c81a00b7a85e8f7364af6784de16a03af1286e451e8c9cc175a94805b83d9"
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

# CADASTRO — desenho
