---
sdd: 1
feature: EXPORTACAO
phase: plan
profile: dev
status: done
upstream:
  path: docs/sdd/EXPORTACAO/design.md
  sha256: "5f0e9f923d32314df1cc3d25eefd1f10793aeeaa986fa22bfbcf42ef4b3787f2"
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

# EXPORTACAO — plano
