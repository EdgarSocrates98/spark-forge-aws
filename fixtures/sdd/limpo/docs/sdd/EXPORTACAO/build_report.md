---
sdd: 1
feature: EXPORTACAO
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/EXPORTACAO/plan.md
  sha256: "00db42c011443e100f8de41745c09f498acb454c0dcd6ee8e52326f9ada370a9"
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
change_id: null
---

# EXPORTACAO — relatorio do build
