---
sdd: 1
feature: ICEBERG_GOLDEN_RECONCILIATION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/ICEBERG_GOLDEN_RECONCILIATION/define.md
  sha256: "7ad8097064c475e829e959ca2c1ecc585e245ea2bb0b6e1e3b1df514e1bae57e"
files:
  - {path: fixtures/iceberg, action: modify, reason: "Reconciliar expected/facts.json, expected/findings.json e meta.yaml das 14 fixtures afetadas."}
  - {path: scripts/regen_fixtures.py, action: modify, reason: "Usar regenerador oficial existente; nenhum código novo é necessário."}
  - {path: tests/test_fixtures_golden_iceberg.py, action: modify, reason: "Nenhuma alteração prevista; manifesto registra o gate que prova o corpus."}
decisions:
  - id: D1
    choice: "Usar scripts/regen_fixtures.py com nomes explícitos e revisar o diff antes do commit."
    rejected: ["Editar JSON manualmente", "Regenerar todos os corpus"]
    rollback: "git revert do commit da reconciliação; os goldens anteriores estão no histórico."
  - id: D2
    choice: "Adicionar iceberg.snapshot a expects_kinds somente onde a entrada contém snapshots observáveis."
    rejected: ["Relaxar o teste de kinds", "Emitir kind sintético em fixture sem snapshots"]
    rollback: "Reverter as alterações dos meta.yaml; o extrator não é alterado."
covers:
  - {part: "fixture expectations", acceptance: [AC1, AC2]}
---

# ICEBERG_GOLDEN_RECONCILIATION — desenho

```text
input/dump.json + extrator atual
             |
             v
scripts/regen_fixtures.py <14 nomes>
             |
             +--> expected/facts.json + expected/findings.json
             +--> meta.yaml expects_kinds atualizado
             v
tests/test_fixtures_golden_iceberg.py
```

O desenho não muda produção: apenas alinha artefatos derivados ao contrato
temporal já entregue.
