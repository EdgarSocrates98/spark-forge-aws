---
sdd: 1
feature: STREAMING_FLINK_PLATFORM
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_PLATFORM/plan.md
  sha256: "23bcb51c82b2383436a254df95c5f5be63d0725304ef3bd2c93125dc010e3bf0"
tasks:
  - id: T1
    status: done
    red:
      command: "python -m pytest tests/test_facts_flink.py::test_flink_dump_emits_job_operator_checkpoint_state tests/test_facts_flink.py::test_managed_flink_dump_keeps_service_namespace -q -p no:cacheprovider --basetemp=C:\\sf-test\\flink-red-t1"
      exit: 2
    green:
      command: "python -m pytest tests/test_facts_flink.py::test_flink_dump_emits_job_operator_checkpoint_state tests/test_facts_flink.py::test_managed_flink_dump_keeps_service_namespace -q -p no:cacheprovider --basetemp=C:\\sf-test\\flink-green-t1"
      exit: 0
  - id: T2
    status: done
    red:
      command: "python -m pytest tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete -q -p no:cacheprovider --basetemp=C:\\sf-test\\flink-red-t2"
      exit: 2
    green:
      command: "python -m pytest tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete -q -p no:cacheprovider --basetemp=C:\\sf-test\\flink-green-t2"
      exit: 0
  - id: T3
    status: done
    red:
      command: "python -m pytest tests/test_analyze_flink.py::test_cli_and_mcp_flink_envelopes_match -q -p no:cacheprovider --basetemp=C:\\sf-test\\flink-red-t3"
      exit: 2
    green:
      command: "python -m pytest tests/test_analyze_flink.py::test_cli_and_mcp_flink_envelopes_match -q -p no:cacheprovider --basetemp=C:\\sf-test\\flink-green-t3"
      exit: 0
  - id: T4
    status: done
    red:
      command: "python scripts/sync_skills.py --check"
      exit: 1
    green:
      command: "python scripts/sync_skills.py --check"
      exit: 0
claims:
  - text: "Flink e Managed Flink emitem namespaces separados e preservam campos ausentes como unresolved."
    evidence_ref: "tests/test_facts_flink.py::test_managed_flink_dump_keeps_service_namespace"
  - text: "O corpus cobre positivo, falha de checkpoint, backpressure observado e métricas ausentes."
    evidence_ref: "tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete"
  - text: "CLI e MCP compartilham o mesmo envelope de análise Flink."
    evidence_ref: "tests/test_analyze_flink.py::test_cli_and_mcp_flink_envelopes_match"
  - text: "Skill, agente, routing, manifesto e espelhos passam sincronização."
    evidence_ref: "python scripts/sync_skills.py --check"
change_id: null
---

# STREAMING_FLINK_PLATFORM — relatório do build

## Desvios do plano

- A skill canônica foi criada em `skills/`; `.agents/skills/` e os demais
  diretórios de plataforma são espelhos gerados pelo `sync_skills.py`.
- O corpus ganhou `managed_unresolved` para provar que ausência de métricas não
  vira zero, e os goldens passaram a comparar findings observados pelas duas
  regras Flink.
- O teste de T4 usa o método existente de paridade do manifesto; não havia um
  teste chamado `test_capability_matrix_is_closed`.

## Revisão

Revisão local em dois estágios: conferência dos critérios contra os fatos,
goldens, regras, superfície e routing; depois conferência dos gates de catálogo,
paridade, skills, referências e surface lock. Nenhum collector live ou mutação
de AWS foi executado.

## Resultado

Implementação concluída para a onda Flink/Managed Flink. A hipótese é confirmada
para o escopo offline desta feature. A matriz de versões upstream↔Managed Flink,
coleta live e limiares operacionais permanecem fora de escopo e unresolved,
conforme o define.
