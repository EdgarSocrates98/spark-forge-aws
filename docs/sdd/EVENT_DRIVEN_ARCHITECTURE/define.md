---
sdd: 1
feature: EVENT_DRIVEN_ARCHITECTURE
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/EVENT_DRIVEN_ARCHITECTURE/explore.md
  sha256: "3264929bf2c4b7a4507b41985d7df1d1380afbfff6cedb11cc81bef9593cc9ad"
hypothesis:
  claim: "Um extractor offline com unresolved explícito torna revisáveis os contratos de arquitetura event-driven sem inventar comportamento runtime."
  prediction: "Fixtures válidas produzem facts estáveis para EventBridge, Pipes, SQS e SNS; artefatos inválidos preservam unresolved; rules acusam somente relações observadas."
  experiment: "Executar extractor, goldens, analyzer CLI/MCP, rules, parity, surface, mirrors, referências, números e bundle offline."
acceptance:
  - id: AC1
    statement: "O extractor emite facts de EventBridge rule/Pipe, SQS queue e SNS topic/subscription e preserva redrive, target e identidade."
    verified_by: {kind: test, ref: tests/test_facts_event_driven.py::test_event_driven_extractor_preserves_dlq_and_targets}
  - id: AC2
    statement: "Artefato inválido ou seção inválida produz event_driven.unresolved e não inventa defaults operacionais."
    verified_by: {kind: test, ref: tests/test_facts_event_driven.py::test_event_driven_extractor_names_invalid_section}
  - id: AC3
    statement: "Goldens cobrem sucesso, lacuna de DLQ, regra sem target e artefato inválido com Fact/Finding válidos."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_event_driven.py::test_event_driven_goldens}
  - id: AC4
    statement: "CLI, core e MCP entregam o mesmo envelope e o tool é read-only."
    verified_by: {kind: test, ref: tests/test_analyze_event_driven.py::test_cli_and_mcp_envelopes_match}
  - id: AC5
    statement: "Rules, routing, skill, mirrors, referências, manifest, surface e offline bundle permanecem sincronizados."
    verified_by: {kind: command, ref: python scripts/check_surface_lock.py}
success:
  - id: SC1
    metric: "AC1–AC5 verdes; nenhum finding declara entrega, exactly-once, replay ou idempotência sem evidência runtime."
    source: "pytest do extractor/analyzer/goldens e gates de catálogo/surface/offline"
out_of_scope:
  - "collector live de EventBridge, Pipes, SQS, SNS ou CloudWatch"
  - "teste de entrega, replay, exactly-once ou idempotência"
  - "mutação de filas, regras, tópicos ou subscriptions"
  - "decision engine entre candidatos de streaming"
unknowns:
  - id: U1
    blocks: [AC1]
    unlock: "Capturar dump produzido por APIs/configuração autorizada contendo target, role, policy, retry e DLQ."
  - id: U2
    blocks: [AC3]
    unlock: "Adicionar caso real sanitizado com retry e subscription redrive quando disponível."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, agent_or_skill, routing, status_numbers]
---

# EVENT_DRIVEN_ARCHITECTURE — definição

Esta wave adiciona contrato factual offline. O sistema segue reportando
blind spots: configuração declarada é evidência de configuração, não prova de
execução.
