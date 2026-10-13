---
sdd: 1
feature: STREAMING_TEMPORAL_EVIDENCE
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_TEMPORAL_EVIDENCE/explore.md
  sha256: "bf363d09f4e0aaef0e15e7f13da39f388313484f8eb409e662f62bb20e9e9adc"
hypothesis:
  claim: "Uma composição temporal offline com timestamps e janela declarados torna verificável se progresso e transporte foram observados juntos, sem afirmar causalidade."
  prediction: "Facts compatíveis produzem um diagnóstico com pares, skew observado e ids de origem; qualquer identidade, timestamp ou janela ausente produz unresolved; a regra só dispara com pelo menos dois pares observados."
  experiment: "Extrair fixtures de progresso/Kafka/Kinesis, compor com tolerância declarada, julgar com runtime, comparar CLI/MCP e executar gates de catálogo, surface, referências, mirrors e bundle offline."
acceptance:
  - id: AC1
    statement: "A composição temporal seleciona query e transporte por identidade declarada, pareia observações deterministically dentro de max_skew_seconds e preserva source_fact_ids, timestamps e causal_inference=false."
    verified_by: {kind: test, ref: tests/test_facts_streaming_temporal.py::test_temporal_pairing_preserves_source_ids_and_skew}
  - id: AC2
    statement: "A composição emite unresolved nomeado quando falta query, transporte, tolerância, timestamp, segunda observação ou par temporal, sem converter ausência em zero."
    verified_by: {kind: test, ref: tests/test_facts_streaming_temporal.py::test_temporal_requires_timestamps_and_declared_window}
  - id: AC3
    statement: "O extractor Kafka preserva timestamp observado do offset e o extractor Kinesis preserva timestamp numérico já fornecido, sem inventar relógio."
    verified_by: {kind: test, ref: tests/test_facts_transport.py::test_transport_preserves_observed_timestamp}
  - id: AC4
    statement: "A regra temporal exige pelo menos duas observações pareadas e mantém finding com evidência não vazia, sem usar threshold fixo de lag ou custo."
    verified_by: {kind: test, ref: tests/test_streaming_rules.py::test_temporal_rule_requires_paired_observations}
  - id: AC5
    statement: "Fixture temporal positiva e fixtures unresolved cobrem Kafka e Kinesis, e a saída esperada mantém o contrato de facts."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming_temporal.py::test_fixture_corpus_is_complete}
  - id: AC6
    statement: "CLI e MCP expõem o mesmo modo temporal, parâmetros e envelope; o surface lock declara a mudança e a tool permanece read-only."
    verified_by: {kind: test, ref: tests/test_analyze_streaming_composition.py::test_temporal_cli_and_mcp_envelopes_match}
  - id: AC7
    statement: "Skill, knowledge, prompt coverage, referência gerada, routing, mirrors e números correntes explicam a janela declarada e preservam os limites live."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "AC1–AC7 verdes; composição sem pares, identidade ou timestamp nunca produz diagnóstico temporal positivo; finding temporal só aparece com dois pares observados."
    source: "pytest focalizado, goldens, judge, CLI/MCP e gates de catálogo/surface/documentação"
out_of_scope:
  - "collector live de Kafka, MSK, Kinesis, CloudWatch ou Spark"
  - "normalização de relógio sem timestamp observado ou inferência pela ordem dos arquivos"
  - "causalidade, SLO, custo, throughput, capacidade, exactly-once ou ganho esperado"
  - "replay funcional e benchmark cloud"
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Fornecer dumps com timestamp/observed_at no formato do serviço e preservar o campo no extractor correspondente."
  - id: U2
    blocks: [AC7]
    unlock: "Atualizar referências geradas e bundle offline após a alteração da superfície e do conhecimento."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, agent_or_skill, status_numbers]
---

# STREAMING_TEMPORAL_EVIDENCE — definição

Esta wave fecha a primeira lacuna temporal sem criar um collector paralelo:
extração continua produzindo Facts; composição recebe identidade e tolerância
declaradas; julgamento continua separado e evidence-first.
