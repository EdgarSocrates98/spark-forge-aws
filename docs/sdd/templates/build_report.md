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
  - text: "O teste de AC1 falhou antes do código e passou depois."
    evidence_ref: "tests/test_exemplo.py::test_exemplo"
change_id: null
---

# EXEMPLO — relatório do build

> Template da skill `sdd-build`. Troque `feature: EXEMPLO` pelo nome da
> feature e ponha `status: draft` ao copiar. `red` é o comando que você VIU
> falhar, com o exit real (diferente de zero); `green` é o mesmo teste
> passando. Quem escreve os dois aqui é o controlador, a partir do relato do
> subagente. Tarefa `skipped` ou `blocked` diz o motivo no corpo. Toda claim
> aponta `evidence_ref`. No perfil `operator`, `change_id` é o id devolvido por
> `sparkforge change sandbox`, e tarefa sem pytest registra `moved`.

## Desvios do plano

Nenhum.

## Revisão

Revisão de spec (fez o que a tarefa pediu, nada a mais) e depois de qualidade,
cada uma por um subagente novo; no fim, a revisão final da implementação
inteira.
