---
sdd: 1
feature: IMPORTACAO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/IMPORTACAO/design.md
  sha256: "3a3476fd5f1057eaccefae3607ad4678a5813139388ee49f09d944aa395fdacc"
tasks:
- id: T1
  files:
  - src/novo.txt
  covers:
  - AC1
  test:
    path: tests/test_alvo.py
    name: test_alvo
---

# IMPORTACAO — plano
