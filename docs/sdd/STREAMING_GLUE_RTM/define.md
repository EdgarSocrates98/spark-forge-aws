---
sdd: 1
feature: STREAMING_GLUE_RTM
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_RTM/explore.md
  sha256: "c3d457ba5183b29cbe1fd2d981c1cb58209ec6d6a850bec0af3e0fc8f9886d42"
hypothesis:
  claim: "Um analyzer offline de jobs Glue preserva runtime, modo RTM, restrições e lacunas de capacidade alcançáveis por CLI e MCP."
  prediction: "Goldens positivos, incompatíveis e unresolved emitem namespaces glue.streaming.*, rules usam somente fatos observados e todas as superfícies retornam o envelope comum."
  experiment: "Rodar facts, goldens, rules, analyzer, skill/parity, routing e surface lock sobre três dumps Glue Streaming/RTM."
acceptance:
  - id: AC1
    statement: "Dumps Glue emitem job, runtime, analyzed e unresolved sem defaults inventados."
    verified_by: {kind: test, ref: tests/test_facts_glue_streaming.py::test_rtm_dump_emits_observed_constraints_and_capacity}
    guard: "Contrato regressivo: facts literais e unresolved não podem mudar por refatoração de parser."
  - id: AC2
    statement: "Fixtures cobrem RTM válido, capacidade ausente e restrições incompatíveis."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_glue_streaming.py::test_glue_streaming_fixture_corpus_is_complete}
    guard: "Contrato regressivo: cada fixture mantém fact kinds e findings ancorados byte a byte."
  - id: AC3
    statement: "CLI e MCP expõem o mesmo analyzer offline e rules têm evidência observada."
    verified_by: {kind: test, ref: tests/test_analyze_glue_streaming.py::test_cli_and_mcp_glue_streaming_envelopes_match}
    guard: "Contrato regressivo: CLI e MCP devem continuar compartilhando o envelope read-only."
  - id: AC4
    statement: "Skill, agente, routing, referências, manifesto e surface ficam sincronizados."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "AC1–AC4 verdes e nenhum finding RTM produzido por campo ausente."
    source: "pytest do corpus Glue Streaming, adapters, regras e gates de integração"
out_of_scope:
  - "collector live Glue/Kafka/Kinesis"
  - "Terraform cross-artifact"
  - "validação funcional de resultado"
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Coletar Terraform e definição efetiva do job para correlação cross-artifact."
  - id: U2
    blocks: [AC2]
    unlock: "Coletar partições/task slots e métricas temporais de uma execução real."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, rule_area, agent_or_skill, status_numbers]
---

# STREAMING_GLUE_RTM — definição
