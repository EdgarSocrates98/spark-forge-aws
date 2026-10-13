---
sdd: 1
feature: GOLDEN_DRIFT_CLOSURE
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/GOLDEN_DRIFT_CLOSURE/plan.md
  sha256: "6547afe6c9e866c333cfd22ab6dc9fc10c053082d0531fa39b19dd0e005e459a"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_streaming_glue_cross_artifact.py -q -p no:cacheprovider --basetemp .pytest-tmp-golden-drift-t1-red", exit: 1}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_scan.py::test_golden[misto] -q -p no:cacheprovider --basetemp .pytest-tmp-golden-drift-t2-red", exit: 1}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_fixtures_scenarios.py::TestGolden::test_assessment_matches_golden -q -p no:cacheprovider --basetemp .pytest-tmp-golden-drift-t3-red", exit: 1}
claims:
  - text: "Glue cross-artifact, scan misto e os três cenários deixam de falhar contra os outputs derivados atuais."
    evidence_ref: "tests/test_fixtures_golden_streaming_glue_cross_artifact.py, tests/test_fixtures_golden_scan.py e tests/test_fixtures_scenarios.py"
  - text: "As alterações de findings Glue são derivadas pelo runner oficial e refletem SF-GLUESTREAM-007 observado, não edição manual."
    evidence_ref: "python scripts/regen_streaming_glue_cross_artifact.py"
  - text: "Nenhum extrator, regra, runtime, CLI ou MCP foi alterado."
    evidence_ref: "git diff --name-only"
change_id: null
---

# GOLDEN_DRIFT_CLOSURE — build

## Entrega

Os sete drifts residuais foram regenerados pelos próprios caminhos usados pelos
testes: `scripts/regen_streaming_glue_cross_artifact.py`, o modo oficial
`SPARKFORGE_REGEN_SCAN=1` para o caso `misto` e `scripts/regen_fixtures.py` para
os três cenários.

## Red/green

- T1 red: **3 failed**; green: **3 passed**.
- T2 red: **1 failed**; green: **1 passed**.
- T3 red: **3 failed**; green: **37 passed** no módulo completo.

## Revisão de escopo

O diff contém facts/findings derivados dos três casos Glue, um summary de scan e
três assessments. Os findings Glue novos são `SF-GLUESTREAM-007`, derivados da
observação `glue.streaming.runtime.unresolved`; não houve edição manual de
findings nem alteração de catálogo.
