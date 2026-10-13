---
sdd: 1
feature: JOB_VENDAS
phase: plan
profile: operator
status: done
upstream:
  path: docs/sdd/JOB_VENDAS/design.md
  sha256: "8d76139abff2ea4cbfe1e060a7055060e9c466533f556ae63238cd7d3f035100"
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

# JOB_VENDAS — plano
