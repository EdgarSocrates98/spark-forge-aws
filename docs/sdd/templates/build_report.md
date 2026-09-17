---
sdd: 1
feature: EXEMPLO
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/EXEMPLO/plan.md
  sha256: ""
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_exemplo.py::test_exemplo -q", exit: 1}
    green: {command: "python -m pytest tests/test_exemplo.py::test_exemplo -q", exit: 0}
claims:
  - text: "O teste de AC1 falhou antes do codigo e passou depois."
    evidence_ref: "tests/test_exemplo.py::test_exemplo"
change_id: null
---

# EXEMPLO — relatorio do build

> Template da skill `sdd-build`. `red` e o comando que voce VIU falhar, com o
> exit real (diferente de zero); `green` e o mesmo teste passando. Tarefa
> `skipped` ou `blocked` diz o motivo no corpo. Toda claim aponta
> `evidence_ref`. No perfil `operator`, `change_id` e o id devolvido por
> `sparkforge change sandbox`.

## Desvios do plano

Nenhum.

## Revisao

Revisao de spec (fez o que a tarefa pediu, nada a mais) e depois de qualidade,
cada uma por um subagente novo.
