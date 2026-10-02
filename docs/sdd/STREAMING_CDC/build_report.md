---
sdd: 1
feature: STREAMING_CDC
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_CDC/plan.md
  sha256: "a4717315c922c1bd117499970cb62e8591bd985eda868ae1d7a70cab248f63bc"
tasks:
  - id: T1
    status: done
    red:
      command: "python -m pytest tests/test_fixtures_golden_cdc.py tests/test_cdc_rules.py -q"
      exit: 1
    green:
      command: "python -m pytest tests/test_facts_cdc.py tests/test_cdc_rules.py tests/test_fixtures_golden_cdc.py -q"
      exit: 0
  - id: T2
    status: done
    red:
      command: "python -m pytest tests/test_fixtures_kind_coverage.py -q"
      exit: 1
    green:
      command: "python -m pytest tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -q"
      exit: 0
  - id: T3
    status: done
    red:
      command: "python scripts/sync_skills.py --check"
      exit: 1
    green:
      command: "python scripts/sync_skills.py --check; python scripts/check_surface_lock.py"
      exit: 0
claims:
  - text: "O extrator preserva semântica observada e nomeia lacunas de CDC."
    evidence_ref: "tests/test_facts_cdc.py::test_cdc_events_preserve_position_transaction_delete_and_duplicate"
  - text: "Cada kind emitido e cada regra CDC têm golden."
    evidence_ref: "tests/test_fixtures_kind_coverage.py::test_every_kind_of_every_extractor_appears_in_some_golden"
  - text: "CLI e MCP compartilham o envelope CDC."
    evidence_ref: "tests/test_analyze_cdc.py::test_cli_and_mcp_cdc_envelopes_match"
change_id: null
---

# STREAMING_CDC — relatório de build

O build corrigiu as duas lacunas encontradas pelos próprios gates: produtor e
golden de `cdc.connector`, e golden explícito para `snapshot_cdc_seam`. O
resultado não afirma compatibilidade, custo, latência ou exatamente-once.
