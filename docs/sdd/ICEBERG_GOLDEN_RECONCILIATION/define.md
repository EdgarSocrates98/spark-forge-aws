---
sdd: 1
feature: ICEBERG_GOLDEN_RECONCILIATION
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/ICEBERG_GOLDEN_RECONCILIATION/explore.md
  sha256: "96b6b9bc50babd7c05e630eadb1725ba5bd121d103931bc1eb79a43c5f7384b4"
hypothesis:
  claim: "Reconciliar goldens legados com a emissão intencional de iceberg.snapshot restaura a prova determinística sem remover evidência temporal."
  prediction: "As 14 fixtures Iceberg deixam de falhar por kind/facts e preservam findings existentes quando as expectativas são regeneradas pelo extrator e pelo catálogo atuais."
  experiment: "Regenerar somente as 14 fixtures Iceberg afetadas pelo script oficial, revisar o diff e executar o corpus completo Iceberg."
acceptance:
  - id: AC1
    statement: "Cada fixture Iceberg declara todos os kinds realmente emitidos, incluindo iceberg.snapshot quando há snapshots observados."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_iceberg.py::TestGolden::test_declared_kinds_all_present"}
  - id: AC2
    statement: "Facts e findings esperados do corpus Iceberg coincidem deterministicamente com o extrator e catálogo atuais."
    verified_by: {kind: command, ref: "python -m pytest tests/test_fixtures_golden_iceberg.py -q -p no:cacheprovider"}
success:
  - id: SC1
    metric: "Fixtures Iceberg que passam no corpus dedicado"
    source: "saída de tests/test_fixtures_golden_iceberg.py"
out_of_scope:
  - "Alterar o extrator iceberg_metadata.py ou regras do catálogo."
  - "Regenerar fixtures de cloudwatch, consumers, Glue, scan ou cenários."
  - "Provar semântica Iceberg live, performance ou compatibilidade de runtime."
unknowns: []
case_id: null
change_kinds: [fixture_corpus]
---

# ICEBERG_GOLDEN_RECONCILIATION — requisitos

Esta fase corrige apenas expectativas derivadas de comportamento já commitado.
O diff de cada fixture deve mostrar o novo fact temporal e nenhuma mudança
manual de finding sem causa observável.
