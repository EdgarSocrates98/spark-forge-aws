---
sdd: 1
feature: SNAPSHOT_GOLDEN_PROPAGATION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SNAPSHOT_GOLDEN_PROPAGATION/plan.md
  sha256: "86a9efa4d390dfb3fe36b80a41bdfa71956f7c21484e56796a2ba396c6be9f9c"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py::TestGolden::test_declared_kinds_all_present tests/test_fixtures_golden_consumers.py::TestGolden::test_declared_kinds_all_present -q -p no:cacheprovider --basetemp .pytest-tmp-snapshot-propagation-red", exit: 1}
claims:
  - text: "Os seis goldens compostos declaram iceberg.snapshot e coincidem com os facts atuais."
    evidence_ref: "python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py tests/test_fixtures_golden_consumers.py -q -p no:cacheprovider --basetemp .pytest-tmp-snapshot-propagation-final"
  - text: "A regeneração alterou somente facts esperados e metadata dos seis casos; nenhum finding esperado mudou."
    evidence_ref: "git diff --name-only -- fixtures/cloudwatch_logs fixtures/consumers"
change_id: null
---

# SNAPSHOT_GOLDEN_PROPAGATION — build

## Entrega

Os seis goldens que reutilizam dumps Iceberg foram regenerados com
`scripts/regen_fixtures.py` usando nomes explícitos. O regenerador atualizou
facts temporais; os seis `meta.yaml` passaram a declarar `iceberg.snapshot`.
Um manifesto com indentação legada foi normalizado para YAML válido durante a
revisão do diff.

## Red/green

- Red: o node de kinds falhou com **6 failed, 29 passed**; todos os diffs eram
  `iceberg.snapshot` emitido e ausente de `expects_kinds`.
- Green focado: o node de kinds fechou **35 passed**.
- Green completo: os dois corpus fecharam **332 passed**.

## Revisão de escopo

O diff contém 12 arquivos: seis `expected/facts.json` e seis `meta.yaml`.
Nenhum `expected/findings.json` mudou. Não houve mudança em extratores, regras,
runtime, CLI ou MCP.
