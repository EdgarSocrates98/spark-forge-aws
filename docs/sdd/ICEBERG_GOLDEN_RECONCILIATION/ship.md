---
sdd: 1
feature: ICEBERG_GOLDEN_RECONCILIATION
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/ICEBERG_GOLDEN_RECONCILIATION/build_report.md
  sha256: "5a5a43dbb77df3ff5d9c049f22e802dd8488e063bbbb5e2ed2f26fb4d046d21f"
hypothesis_outcome: confirmed
registries: [fixture_corpus_gates]
deviations:
  - "snapshot_churn adicionou 604 observações temporais e 16.200 linhas ao diff; o volume é derivado do dump e foi preservado para não perder evidência."
  - "A regeneração usou scripts/regen_fixtures.py existente, sem alteração no regenerador ou no runtime."
---

# ICEBERG_GOLDEN_RECONCILIATION — entrega

## Hipótese

Confirmada. O drift estava no corpus: o extrator temporal já emitia
`iceberg.snapshot`, mas 14 goldens não declaravam nem armazenavam esse kind. A
regeneração oficial alinhou facts e `expects_kinds` sem alterar regras, findings ou
código de produção.

## Gates rodados

- `python -m pytest tests/test_fixtures_golden_iceberg.py::TestGolden::test_declared_kinds_all_present -q -p no:cacheprovider --basetemp .pytest-tmp-iceberg-kinds-green` — `14 passed`.
- `python -m pytest tests/test_fixtures_golden_iceberg.py -q -p no:cacheprovider --basetemp .pytest-tmp-iceberg-green` — `94 passed`.
- `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py -q -p no:cacheprovider --basetemp .pytest-tmp-iceberg-corpus-gate` — `116 passed`.
- `sparkforge sdd check --repo . --feature ICEBERG_GOLDEN_RECONCILIATION` — `ok: true`.

## Limites

Este ship prova coerência determinística do corpus e cobertura do wheel, não prova
execução Iceberg em AWS, desempenho, custo ou semântica de snapshots fora dos dumps
versionados.

## Lições

- Quando um extrator ganha um kind temporal, o contrato precisa evoluir junto em
  `expected/facts.json` e `meta.yaml`; o teste de kinds captura o drift antes do
  golden completo.
- Goldens de churn podem ser grandes por natureza; reduzir observações para encurtar
  diff quebraria a rastreabilidade do artefato.
