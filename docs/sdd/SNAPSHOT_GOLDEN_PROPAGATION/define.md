---
sdd: 1
feature: SNAPSHOT_GOLDEN_PROPAGATION
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/SNAPSHOT_GOLDEN_PROPAGATION/explore.md
  sha256: "7dc2f344fe54416a11f8cd2bb53e36463aaca16948ead1eb60d944ae5fd9d06c"
hypothesis:
  claim: "Propagar iceberg.snapshot aos runners compostos restaura a prova determinística sem alterar produção."
  prediction: "As seis fixtures deixam de falhar por facts/kinds e findings permanecem estáveis."
  experiment: "Regenerar somente seis nomes pelos regeneradores oficiais, revisar o diff e executar os dois corpus."
acceptance:
  - id: AC1
    statement: "As seis fixtures afetadas declaram e preservam iceberg.snapshot."
    verified_by: {kind: command, ref: "python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py tests/test_fixtures_golden_consumers.py -q -p no:cacheprovider"}
  - id: AC2
    statement: "Os dois corpus completos permanecem verdes e findings não mudam."
    verified_by: {kind: command, ref: "python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py tests/test_fixtures_golden_consumers.py -q -p no:cacheprovider"}
success:
  - id: SC1
    metric: "Fixtures compostas que passam nos dois corpus"
    source: "saída dos dois módulos de golden"
out_of_scope:
  - "Alterar extratores, regras, Glue cross-artifact, scan ou cenários."
  - "Provar semântica Iceberg live, performance ou runtime cloud."
unknowns: []
case_id: null
change_kinds: [fixture_corpus]
---

# SNAPSHOT_GOLDEN_PROPAGATION — definição

## Critérios de aceite

- AC1: nenhum runner composto perde o kind temporal emitido pelo extrator.
- AC2: facts, kinds e findings permanecem coerentes nos dois corpus.

Não há mudança de runtime, catálogo, regra, CLI ou MCP. O ganho é de
reauditabilidade do corpus, não de performance.
