---
sdd: 1
feature: GOLDEN_DRIFT_CLOSURE
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/GOLDEN_DRIFT_CLOSURE/explore.md
  sha256: "e4c586d1593bc214b123ba58f65c81fb347f608805cf98f2ea52b4097c8193e8"
hypothesis:
  claim: "Regenerar os sete goldens residuais pelos runners oficiais restaura paridade sem alterar regras ou runtime."
  prediction: "Os três corpus deixam de falhar e nenhum finding/assessment é editado manualmente."
  experiment: "Regenerar somente os casos explicitamente falhos, revisar diff e executar os módulos completos."
acceptance:
  - id: AC1
    statement: "Glue cross-artifact tem facts e findings esperados alinhados ao fuse atual."
    verified_by: {kind: command, ref: "python scripts/regen_streaming_glue_cross_artifact.py e python -m pytest tests/test_fixtures_golden_streaming_glue_cross_artifact.py -q -p no:cacheprovider"}
  - id: AC2
    statement: "O golden de scan misto reflete o número atual de facts sem alterar o contrato do scan."
    verified_by: {kind: command, ref: "SPARKFORGE_REGEN_SCAN=1 python -m pytest tests/test_fixtures_golden_scan.py::test_golden[misto] -q -p no:cacheprovider"}
  - id: AC3
    statement: "Os três cenários de migração refletem o catálogo atual e permanecem determinísticos."
    verified_by: {kind: command, ref: "python scripts/regen_fixtures.py glue_40_para_60_salto_longo glue_51_para_60_iceberg_ansi glue_60_fgac_com_jar e python -m pytest tests/test_fixtures_scenarios.py -q -p no:cacheprovider"}
success:
  - id: SC1
    metric: "Falhas nos três corpus residuais"
    source: "execução dos módulos de golden"
out_of_scope:
  - "Alterar extratores, regras, runtime, CLI ou MCP."
  - "Regenerar corpus não falho ou atribuir ganho de performance."
unknowns: []
case_id: null
change_kinds: [fixture_corpus]
---

# GOLDEN_DRIFT_CLOSURE — definição

O scope é estritamente corpus: outputs esperados derivados pelo código atual,
com revisão para rejeitar alterações de findings/assessment sem causa observada.
