---
sdd: 1
feature: EVENT_DRIVEN_ARCHITECTURE
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/EVENT_DRIVEN_ARCHITECTURE/plan.md
  sha256: "76c20e33c15b1ed6939031975cd0ce3d53a928046abb4f804c00caeddf05f81c"
tasks:
  - {id: T1, status: done, red: {command: "python -m pytest tests/test_facts_event_driven.py -q", exit: 2}, green: {command: "python -m pytest tests/test_facts_event_driven.py -q", exit: 0}}
  - {id: T2, status: done, red: {command: "python -m pytest tests/test_fixtures_golden_event_driven.py -q", exit: 2}, green: {command: "python -m pytest tests/test_fixtures_golden_event_driven.py -q", exit: 0}}
  - {id: T3, status: done, red: {command: "python -m pytest tests/test_analyze_event_driven.py -q", exit: 2}, green: {command: "python -m pytest tests/test_analyze_event_driven.py -q", exit: 0}}
  - {id: T4, status: done, red: {command: "python scripts/check_surface_lock.py", exit: 1}, green: {command: "python scripts/check_surface_lock.py", exit: 0}}
claims:
  - text: "Facts EventBridge/Pipes/SQS/SNS preservam procedência e unresolved."
    evidence_ref: "tests/test_facts_event_driven.py::test_event_driven_extractor_names_invalid_section"
  - text: "CLI e MCP expõem o mesmo envelope read-only."
    evidence_ref: "tests/test_analyze_event_driven.py::test_cli_and_mcp_envelopes_match"
change_id: null
---

# EVENT_DRIVEN_ARCHITECTURE — relatório do build

Build concluído com extractor, rules, fixtures, analyzer, skill, routing,
surface, mirrors, referências, números correntes e bundle offline validados.
