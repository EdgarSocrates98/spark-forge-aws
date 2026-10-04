---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY/explore.md
  sha256: "ed8b5e19deb994a31b36145c01772a345afdd72ed64b799d365144b18700b3f7"
hypothesis:
  claim: "Um analyzer offline de Schema Registry torna evolução, compatibilidade e auto-registro julgáveis por facts ancorados."
  prediction: "Goldens positivo, incompatível, auto-registro, política ausente e JSON inválido mantêm namespaces e unresolved separados."
  experiment: "Rodar extrator, regras, goldens, CLI/MCP, cobertura, routing e gates derivados."
acceptance:
  - id: AC1
    statement: "Registry, subject, formato, versão, campos, obrigatoriedade, política e diff são extraídos sem inferência."
    verified_by: {kind: test, ref: tests/test_facts_schema_registry.py::test_schema_registry_extracts_diff_and_unresolved_policy}
    guard: "Contrato regressivo: facts estruturais e unresolved permanecem ancorados."
  - id: AC2
    statement: "Regras cobrem incompatibilidade, auto-registro e compatibilidade não declarada."
    verified_by: {kind: test, ref: tests/test_schema_registry_rules.py::test_incompatible_schema_and_auto_registration_are_findings}
    guard: "Contrato regressivo: findings exigem evidence e rule_id do catálogo."
  - id: AC3
    statement: "Fixtures positivas, negativas e unresolved exercitam cada kind e cada regra."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_schema_registry.py::test_schema_registry_fixture_goldens}
    guard: "Contrato regressivo: goldens permanecem determinísticos."
  - id: AC4
    statement: "CLI e MCP compartilham envelope e tool read-only."
    verified_by: {kind: test, ref: tests/test_analyze_schema_registry.py::test_cli_and_mcp_schema_registry_envelopes_match}
    guard: "Contrato regressivo: portas não divergem."
  - id: AC5
    statement: "Skill, agente, routing, knowledge, parity, superfície e referências ficam sincronizados."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
    guard: "Contrato regressivo: mirrors e locks continuam idempotentes."
success:
  - {id: SC1, metric: "AC1–AC5 verdes", source: "pytest e gates do repositório"}
out_of_scope:
  - "compatibilidade real contra registry remoto e consumidores vivos"
  - "mutação ou publicação de schema"
  - "semântica completa de Avro, JSON Schema ou Protobuf"
unknowns:
  - {id: U1, blocks: [AC1], unlock: "Coletar configuração efetiva e consumidores versionados."}
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, rule_area, agent_or_skill, status_numbers]
---

# STREAMING_SCHEMA_REGISTRY — definição
