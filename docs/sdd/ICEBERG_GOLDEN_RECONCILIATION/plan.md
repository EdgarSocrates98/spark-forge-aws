---
sdd: 1
feature: ICEBERG_GOLDEN_RECONCILIATION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/ICEBERG_GOLDEN_RECONCILIATION/design.md
  sha256: "6065aeaa45f4d6ed26cd31b902973b6b76faca7558f05afdf21c00216c26f476"
tasks:
  - id: T1
    files: [fixtures/iceberg, tests/test_fixtures_golden_iceberg.py]
    covers: [AC1, AC2]
    test: {path: tests/test_fixtures_golden_iceberg.py, name: "TestGolden::test_declared_kinds_all_present"}
---

# ICEBERG_GOLDEN_RECONCILIATION — plano

## T1 — reconciliar corpus Iceberg

1. Rodar o node `TestGolden::test_declared_kinds_all_present` e registrar o
   red observado (`iceberg.snapshot` extra).
2. Executar `python scripts/regen_fixtures.py` somente para os 14 nomes do
   corpus Iceberg: `delete_content_separado`, `delete_debt`, `format_v1_valida`,
   `format_v3_com_propriedade`, `format_version_ausente_no_dump`,
   `format_version_diverge_da_propriedade`, `healthy_table`,
   `metadata_tables_full`, `small_files`, `small_files_at_p1_boundary`,
   `snapshot_churn`, `sort_order_debt`, `sort_order_rewritten` e
   `sort_order_unknown`.
3. Atualizar `expects_kinds` em cada `meta.yaml` para incluir
   `iceberg.snapshot` quando o dump o emite; revisar diff de facts/findings e
   rejeitar qualquer mudança fora do novo fact temporal.
4. Rodar o mesmo node verde e o corpus completo Iceberg.

Commit: `test(iceberg): reconcile temporal snapshot goldens`
