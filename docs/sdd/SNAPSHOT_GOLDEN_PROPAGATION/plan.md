---
sdd: 1
feature: SNAPSHOT_GOLDEN_PROPAGATION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SNAPSHOT_GOLDEN_PROPAGATION/design.md
  sha256: "6480ed4064911fbaa81188e3b7ac5e80f82d52eba27eacc7902206ad2a9a57a3"
tasks:
  - id: T1
    files: [fixtures/cloudwatch_logs, fixtures/consumers]
    covers: [AC1, AC2]
    test: {path: tests/test_fixtures_golden_cloudwatch_logs.py, name: "TestGolden::test_declared_kinds_all_present"}
---

# SNAPSHOT_GOLDEN_PROPAGATION — plano

1. Rodar os nodes de facts/kinds e registrar o red observado.
2. Executar `python scripts/regen_fixtures.py` somente para:
   `athena_v3_confirmado_no_log`, `athena_v3_sem_inventario`,
   `commit_conflict_com_snapshots`, `v2_with_athena_consumer`,
   `v3_sem_propriedade_com_athena` e `v3_with_athena_consumer`.
3. Atualizar `expects_kinds` se necessário e rejeitar qualquer alteração em
   findings esperados.
4. Rodar os dois módulos completos e o gate de corpus.

Commit: `test(fixtures): propagate Iceberg snapshots to composed goldens`
