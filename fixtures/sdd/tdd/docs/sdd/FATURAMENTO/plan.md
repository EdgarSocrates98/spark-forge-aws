---
sdd: 1
feature: FATURAMENTO
phase: plan
profile: dev
status: done
upstream:
  path: docs/sdd/FATURAMENTO/design.md
  sha256: "81495f3fcc765018e952a751cda506f730e124a1f13ea229168ec6c4aa2fc628"
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

# FATURAMENTO — plano
