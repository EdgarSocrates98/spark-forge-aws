---
sdd: 1
feature: EXPORTACAO
phase: define
profile: dev
status: done
hypothesis:
  claim: O relatorio sintetico sai com o total certo.
  prediction: O teste alvo passa.
  experiment: Rodar tests/test_alvo.py.
acceptance:
- id: AC1
  statement: Criterio sintetico AC1.
  verified_by:
    kind: test
    ref: tests/test_alvo.py::test_alvo
success:
- id: SC1
  metric: Testes verdes
  source: tests/test_alvo.py
out_of_scope: []
change_kinds: []
---

# EXPORTACAO — requisitos

Fixture sintetica do eval do SDD.
