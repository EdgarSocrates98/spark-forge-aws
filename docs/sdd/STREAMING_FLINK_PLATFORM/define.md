---
sdd: 1
feature: STREAMING_FLINK_PLATFORM
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_PLATFORM/explore.md
  sha256: "1efcb63d780f027376eef026f6ce99c3de4e2ff60e35cfbc6b379ee4075478f7"
hypothesis:
  claim: "Um analyzer comum preserva diferenças entre Flink upstream e Managed Flink e torna checkpoint/backpressure/state observados alcançáveis por CLI e MCP."
  prediction: "Goldens por domínio emitem namespaces separados, campos ausentes viram unresolved, regras só disparam sobre métricas observadas e CLI/MCP retornam o mesmo envelope."
  experiment: "Rodar facts, goldens, analyzer, regras, skill/parity e surface lock sobre fixtures Flink e Managed Flink."
acceptance:
  - id: AC1
    statement: "Dumps Flink emitem facts de job, operator, checkpoint, state e unresolved sem defaults inventados."
    verified_by: {kind: test, ref: tests/test_facts_flink.py::test_flink_dump_emits_job_operator_checkpoint_state}
  - id: AC2
    statement: "Dumps Managed Flink emitem application/config e preservam unresolved de métricas ausentes."
    verified_by: {kind: test, ref: tests/test_facts_flink.py::test_managed_flink_dump_keeps_service_namespace}
  - id: AC3
    statement: "Fixtures cobrem positivo, falha de checkpoint, backpressure observado e unresolved."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete}
  - id: AC4
    statement: "CLI e MCP compartilham analyzer Flink e rules exigem evidência observada."
    verified_by: {kind: test, ref: tests/test_analyze_flink.py::test_cli_and_mcp_flink_envelopes_match}
  - id: AC5
    statement: "Skill, agente, routing, referências e surface ficam sincronizados."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "AC1–AC5 verdes e nenhum finding Flink produzido por campo ausente."
    source: "pytest do corpus Flink, analyzer e regras; gates de sync/surface/offline"
out_of_scope:
  - "collector live AWS Managed Flink"
  - "matriz completa de releases Flink upstream↔Managed Flink"
  - "limiar de backpressure, custo ou capacidade sem baseline"
  - "alteração de job ou infraestrutura"
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Coletar descrição/configuração real de aplicação Managed Flink com runtime e connectors."
  - id: U2
    blocks: [AC1, AC3]
    unlock: "Coletar série temporal de métricas de checkpoint/backpressure e state."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, rule_area, agent_or_skill, status_numbers]
---

# STREAMING_FLINK_PLATFORM — definição

Esta wave cria o primeiro contrato determinístico de Flink. Toda ausência
permanece nomeada; nenhum namespace `flink.*` é usado para afirmar uma
capacidade de Managed Flink.
