---
sdd: 1
feature: STREAMING_CDC
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_CDC/explore.md
  sha256: "f4c7f9b73d10059e43b21bc10cdaa0654a477812c047f08180ff91b80493832d"
hypothesis:
  claim: "Um analyzer CDC offline torna posição, chave, transação, snapshot/CDC seam, tombstone, Debezium schema history e DMS scope alcançáveis por facts ancorados, CLI/MCP e routing."
  prediction: "Goldens cobrem caminho feliz, duplicata/delete sem tombstone, chave/corte ausentes, Debezium incompleto e DMS incompleto; nenhuma regra dispara sem observação correspondente."
  experiment: "Rodar extrator, corpus golden, rules, analyzer CLI/MCP, paridade, cobertura de kinds, reachability, offline manifest, surface e SDD."
acceptance:
  - id: AC1
    statement: "Eventos CDC preservam operação, posição, chave, transação, snapshot, tombstone, duplicata e unresolved."
    verified_by: {kind: test, ref: tests/test_facts_cdc.py::test_cdc_events_preserve_position_transaction_delete_and_duplicate}
    guard: "Contrato regressivo: facts de posição, chave, transação e unresolved não podem mudar por refatoração do parser."
  - id: AC2
    statement: "Debezium e DMS emitem namespaces próprios, configuração observada e unresolved para lacunas materiais."
    verified_by: {kind: test, ref: tests/test_facts_cdc.py::test_debezium_and_dms_keep_configuration_and_unresolved_separate}
    guard: "Contrato regressivo: namespaces Debezium e DMS permanecem separados e lacunas continuam nomeadas."
  - id: AC3
    statement: "Fixtures cobrem eventos, connector, JSON inválido, snapshot/CDC seam, Debezium e DMS; cada kind e regra tem golden."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_cdc.py::test_cdc_fixture_corpus_is_complete}
    guard: "Contrato regressivo: cada fixture mantém fact kinds, findings e unresolved ancorados byte a byte."
  - id: AC4
    statement: "CLI e MCP retornam o mesmo envelope e a tool é read-only com schema declarado."
    verified_by: {kind: test, ref: tests/test_analyze_cdc.py::test_cli_and_mcp_cdc_envelopes_match}
    guard: "Contrato regressivo: CLI e MCP continuam compartilhando o envelope read-only."
  - id: AC5
    statement: "Skill, agente, routing, manifesto, espelhos, fontes e superfície ficam sincronizados."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
    guard: "Contrato regressivo: espelhos, referências, routing, manifest e surface lock permanecem sincronizados."
success:
  - id: SC1
    metric: "AC1–AC5 verdes; nenhum finding CDC nasce de campo ausente ou namespace de outro domínio."
    source: "pytest do corpus CDC, analyzer, regras e gates de sincronização"
out_of_scope:
  - "collector live de Debezium, Kafka Connect ou AWS DMS"
  - "matriz completa de versões e compatibilidade de conectores"
  - "schema registry e evolução de contrato"
  - "replay, benchmark, custo, throughput ou prova de exatamente-once"
  - "alteração em banco, broker, connector ou AWS"
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Coletar configuração/status efetivos e runtime do conector ou task, sem segredos."
  - id: U2
    blocks: [AC3, AC4]
    unlock: "Correlacionar posição de corte, consumidor e resultado funcional em replay controlado."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, rule_area, agent_or_skill, status_numbers]
---

# STREAMING_CDC — definição

A wave fecha o contrato offline e deixa explícitos os artefatos que ainda
destravariam uma decisão operacional.
