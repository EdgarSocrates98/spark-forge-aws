---
sdd: 1
feature: STREAMING_GLUE_RTM
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_RTM/plan.md
  sha256: "0dd956f7be83cdb5dacb4fa29f3933e8d77219272d0ed8af66507404175839a1"
tasks:
  - id: T1
    status: done
    red:
      command: "python -m pytest tests/test_facts_glue_streaming.py tests/test_glue_streaming_rules.py tests/test_fixtures_golden_glue_streaming.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\glue-streaming-red-domain"
      exit: 1
    green:
      command: "python -m pytest tests/test_facts_glue_streaming.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\glue-streaming-facts"
      exit: 0
  - id: T2
    status: done
    red:
      command: "python -m pytest tests/test_facts_glue_streaming.py tests/test_glue_streaming_rules.py tests/test_fixtures_golden_glue_streaming.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\glue-streaming-red-domain"
      exit: 1
    green:
      command: "python -m pytest tests/test_glue_streaming_rules.py tests/test_fixtures_golden_glue_streaming.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\glue-streaming-goldens"
      exit: 0
  - id: T3
    status: done
    red:
      command: "python -m pytest tests/test_adapters_tools.py tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py tests/test_host_surface_contracts.py tests/test_adapters_mcp_compact.py tests/test_capability_parity.py tests/test_offline_expansion.py tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\glue-streaming-red-integration"
      exit: 1
    green:
      command: "python -m pytest tests/test_adapters_tools.py -q -p no:cacheprovider --basetemp=C:\\sf-test\\glue-streaming-surface"
      exit: 0
  - id: T4
    status: done
    red:
      command: "python scripts/check_status_numbers.py --strict"
      exit: 1
    green:
      command: "python scripts/sync_skills.py --check; python scripts/check_surface_lock.py; python scripts/check_status_numbers.py --strict"
      exit: 0
claims:
  - text: "O extrator Glue preserva restrições observadas e ausência de capacidade como unresolved."
    evidence_ref: "tests/test_facts_glue_streaming.py::test_rtm_missing_capacity_is_unresolved_not_zero"
  - text: "O corpus cobre RTM válido, restrições incompatíveis e capacidade ausente."
    evidence_ref: "tests/test_fixtures_golden_glue_streaming.py::test_glue_streaming_fixture_corpus_is_complete"
  - text: "A tool Glue Streaming retorna saída compatível com o schema declarado."
    evidence_ref: "tests/test_analyze_glue_streaming.py::test_cli_and_mcp_glue_streaming_envelopes_match"
  - text: "Skill, agente, routing, manifesto e espelhos passam sincronização."
    evidence_ref: "python scripts/sync_skills.py --check"
change_id: null
---

# STREAMING_GLUE_RTM — relatório de build

O build foi guiado pelos contratos offline: ausência permaneceu unresolved,
rules foram limitadas a observações e a superfície reutilizou o mesmo envelope
de facts. O resultado não afirma compatibilidade produtiva, custo, latência ou
ganho sem artefatos de execução.
