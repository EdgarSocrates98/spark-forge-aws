---
sdd: 1
feature: STREAMING_LAKEHOUSE_OBSERVABILITY
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_LAKEHOUSE_OBSERVABILITY/explore.md
  sha256: "fcdd510bed0c74aa9e081ff0d599b2b4455d19e1d543b69aa14f5d944c926302"
hypothesis:
  claim: "Uma composição offline com vínculo declarado torna observáveis as relações entre progresso, transporte e Iceberg sem inventar causalidade."
  prediction: "Entradas compatíveis produzem facts compostos com ids de origem, entradas incompletas produzem unresolved e regras só avaliam relações observadas."
  experiment: "Rodar fatos, goldens, composição, rules, CLI/MCP, routing e gates de surface sobre cenários Iceberg e observabilidade."
acceptance:
  - id: AC1
    statement: "A composição streaming→Iceberg exige query/tabela declaradas e preserva snapshot, operação, progresso e procedência."
    verified_by: {kind: test, ref: tests/test_facts_streaming_composition.py::test_iceberg_link_requires_declared_identity}
  - id: AC2
    statement: "A composição progresso→transporte preserva lag ou iterator age observado e não converte ausência em zero."
    verified_by: {kind: test, ref: tests/test_facts_streaming_composition.py::test_observability_link_preserves_transport_measurement}
  - id: AC3
    statement: "Fixtures cobrem relação Iceberg não-append, relação observável sem finding causal e unresolved."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming_composition.py::test_fixture_corpus_is_complete}
  - id: AC4
    statement: "CLI e MCP compartilham a mesma composição e retornam o mesmo envelope."
    verified_by: {kind: test, ref: tests/test_analyze_streaming_composition.py::test_cli_and_mcp_envelopes_match}
  - id: AC5
    statement: "Rules, skill, routing, references, mirrors e surface lock permanecem sincronizados."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "AC1–AC5 verdes; nenhum finding é produzido por vínculo ausente ou por limiar de custo/lag inventado."
    source: "pytest do correlator, fixtures, analyzer e gates de catálogo/surface"
out_of_scope:
  - "collector live de Kafka, Kinesis, CloudWatch ou Iceberg"
  - "inferência causal entre lag, processamento, commit e tamanho de arquivo"
  - "SLO, custo, throughput ou limiar operacional sem baseline declarado"
  - "linhagem observada fora dos dois vínculos explícitos desta wave"
unknowns:
  - id: U1
    blocks: [AC1]
    unlock: "Capturar identidade estável da query e tabela no artefato de execução."
  - id: U2
    blocks: [AC2]
    unlock: "Coletar série temporal pareada de lag/iterator age e progresso na mesma janela."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, agent_or_skill, status_numbers]
---

# STREAMING_LAKEHOUSE_OBSERVABILITY — definição

Esta wave adiciona composição, não um segundo parser: cada observação continua
com seu extractor e a ligação só existe quando a identidade é declarada e
encontrada nos facts.
