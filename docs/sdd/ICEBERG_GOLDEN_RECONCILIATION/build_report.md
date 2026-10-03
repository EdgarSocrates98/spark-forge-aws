---
sdd: 1
feature: ICEBERG_GOLDEN_RECONCILIATION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/ICEBERG_GOLDEN_RECONCILIATION/plan.md
  sha256: "012cfe8951c750a545aacea5eaff288af90ed8097082e34f3f6e30ddb31bb139"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_iceberg.py::TestGolden::test_declared_kinds_all_present -q -p no:cacheprovider --basetemp .pytest-tmp-iceberg-kinds-red", exit: 1}
claims:
  - text: "Os 14 goldens Iceberg declaram iceberg.snapshot quando o extrator temporal o emite."
    evidence_ref: "python -m pytest tests/test_fixtures_golden_iceberg.py::TestGolden::test_declared_kinds_all_present -q -p no:cacheprovider --basetemp .pytest-tmp-iceberg-kinds-green"
  - text: "O corpus Iceberg completo permanece coerente após a regeneração."
    evidence_ref: "python -m pytest tests/test_fixtures_golden_iceberg.py -q -p no:cacheprovider --basetemp .pytest-tmp-iceberg-green"
  - text: "A reconciliação não alterou findings esperados nem código de produção."
    evidence_ref: "git diff --name-only e revisão dos diffs de expected/findings.json"
change_id: null
---

# ICEBERG_GOLDEN_RECONCILIATION — build

Implementação fechada. O extrator temporal já emitia `iceberg.snapshot`; o corpus
Iceberg estava atrasado em relação ao contrato executável. A correção regenerou os
facts dos 14 goldens afetados e declarou o kind em seus `meta.yaml`, sem alteração
de produção, de regras ou de findings esperados.

`snapshot_churn` adiciona 604 observações temporais, refletidas em 16.200 linhas do
diff. Esse volume é evidência do dump, não expansão artificial do contrato.

## Critérios aceitos

- AC1: o kind declarado é produzido em todas as 14 fixtures afetadas — 14/14
  passaram no node vermelho/verde.
- AC2: o corpus completo permanece coerente — 94 testes passaram.

## Gates executados

- `python -m pytest tests/test_fixtures_golden_iceberg.py -q -p no:cacheprovider`
- diff revisado: somente `expected/facts.json` e `meta.yaml` das 14 fixtures;
  nenhum `expected/findings.json` alterado.

Nenhuma mudança de runtime foi necessária; o drift era de corpus e foi tratado como
`fixture_corpus`.
