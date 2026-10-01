---
sdd: 1
feature: JOB_VENDAS
phase: build_report
profile: operator
status: ready
upstream:
  path: docs/sdd/JOB_VENDAS/plan.md
  sha256: "71a3707a16025eb78a51405a202584692feaa4f21e8331ea517f008f21265a3a"
tasks:
- id: T1
  status: done
  red:
    command: python -m pytest tests/test_alvo.py -q
    exit: 1
  green:
    command: python -m pytest tests/test_alvo.py -q
    exit: 0
claims:
- text: O teste alvo passa.
  evidence_ref: tests/test_alvo.py::test_alvo
change_id: SANDBOX-AUSENTE
---

# JOB_VENDAS — relatorio do build
