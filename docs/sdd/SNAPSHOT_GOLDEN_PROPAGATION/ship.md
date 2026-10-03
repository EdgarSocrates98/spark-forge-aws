---
sdd: 1
feature: SNAPSHOT_GOLDEN_PROPAGATION
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SNAPSHOT_GOLDEN_PROPAGATION/build_report.md
  sha256: "7a9993ac223fdc4efb03bd3f51f4b6ab1e0c05c225b16889419c3735184ac1f6"
hypothesis_outcome: confirmed
registries: [fixture_corpus_gates]
deviations:
  - "Um meta.yaml legado exigiu normalização de indentação para que a declaração de iceberg.snapshot fosse YAML válido; sem alteração semântica além do kind declarado."
---

# SNAPSHOT_GOLDEN_PROPAGATION — entrega

## Hipótese

Confirmada. Os runners de CloudWatch Logs e Consumers reutilizam o extrator
Iceberg e agora preservam `iceberg.snapshot` nos seis casos afetados. Facts,
kinds e findings estão novamente alinhados ao comportamento observado.

## Gates rodados

- `python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py::TestGolden::test_declared_kinds_all_present tests/test_fixtures_golden_consumers.py::TestGolden::test_declared_kinds_all_present -q -p no:cacheprovider` — `35 passed`.
- `python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py tests/test_fixtures_golden_consumers.py -q -p no:cacheprovider` — `332 passed`.
- `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py -q -p no:cacheprovider --basetemp .pytest-tmp-snapshot-propagation-corpus-gate` — `116 passed`.
- `sparkforge sdd check --repo . --feature SNAPSHOT_GOLDEN_PROPAGATION` — `ok: true`.

## Limites

Este ship prova coerência local dos dois runners; não prova Iceberg live,
performance, custo, semântica cloud ou validade de snapshots não presentes nos
dumps versionados.
