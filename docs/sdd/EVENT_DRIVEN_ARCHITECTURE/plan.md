---
sdd: 1
feature: EVENT_DRIVEN_ARCHITECTURE
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/EVENT_DRIVEN_ARCHITECTURE/design.md
  sha256: "0eafbe347401edcac7c0da565a68f64b63394585f662e99c2df2ea1850b8b9e7"
tasks:
  - {id: T1, files: [sparkforge_aws/facts/event_driven.py, tests/test_facts_event_driven.py], covers: [AC1, AC2], test: {path: tests/test_facts_event_driven.py, name: test_event_driven_extractor_preserves_dlq_and_targets}}
  - {id: T2, files: [fixtures/event_driven, tests/test_fixtures_golden_event_driven.py, rules/catalog/event-driven.yaml], covers: [AC3], test: {path: tests/test_fixtures_golden_event_driven.py, name: test_event_driven_goldens}}
  - {id: T3, files: [sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py, tests/test_analyze_event_driven.py], covers: [AC4], test: {path: tests/test_analyze_event_driven.py, name: test_cli_and_mcp_envelopes_match}}
  - {id: T4, files: [skills/review-event-driven-architecture/SKILL.md, agents/streaming-realtime-architect.md, rules/catalog/routing.yaml, parity.yaml, manifest.json, docs/streaming/prompt-coverage.md], covers: [AC5], test: {path: tests/test_capability_parity.py, name: "TestManifestMatchesReality::test_every_declared_tool_exists_in_the_tool_surface"}}
---

# EVENT_DRIVEN_ARCHITECTURE — plano

Validar primeiro fatos e goldens; depois surface e integrações geradas; por
fim executar gates de catálogo, status, mirrors, referências e bundle offline.
