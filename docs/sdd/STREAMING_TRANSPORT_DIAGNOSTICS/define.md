---
sdd: 1
feature: STREAMING_TRANSPORT_DIAGNOSTICS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_TRANSPORT_DIAGNOSTICS/explore.md
  sha256: "eaff7d5535690065648428dd7b154440054a77554d5b2e412154d1efb2da98db"
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb]
acceptance:
  - id: AC1
    statement: "Kafka topic, partition, consumer group e lag facts preservam âncoras, offsets e distribuição por partition quando presentes."
    verified_by: {kind: test, ref: tests/test_facts_transport.py::test_kafka_dump_emits_topic_partition_group_and_lag_facts}
  - id: AC2
    statement: "MSK e Kinesis facts preservam versão/broker/security e stream/shard/metric sem confundir ausência com zero."
    verified_by: {kind: test, ref: tests/test_facts_transport.py::test_msk_and_kinesis_dump_emit_observed_facts}
  - id: AC3
    statement: "JSON inválido, shape desconhecido e artefato sem distribuição emitem unresolved nomeado."
    verified_by: {kind: test, ref: tests/test_facts_transport.py::test_transport_blind_spots_are_unresolved}
  - id: AC4
    statement: "CLI e MCP compartilham o envelope do analyzer e não acessam rede."
    verified_by: {kind: test, ref: tests/test_analyze_transport.py::test_cli_and_mcp_transport_envelopes_match}
  - id: AC5
    statement: "Corpus golden cobre Kafka, MSK, Kinesis e unresolved; knowledge e locks são offline e verificáveis."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_transport.py::test_transport_fixture_corpus_is_complete}
  - id: AC6
    statement: "Surface pública, capability/parity e referências geradas ficam sincronizadas."
    verified_by: {kind: command, ref: python scripts/check_surface_lock.py}
prediction:
  statement: "Um contrato comum reduzirá duplicação de envelope sem apagar diferenças entre Kafka, MSK e Kinesis, e dará ao agente facts suficientes para pedir o próximo artefato sem afirmar causa."
  measure: "Comparar golden facts por domínio, count de unresolved e igualdade CLI/MCP; não medir ganho de performance."
  falsifier: "Se qualquer domínio perder sua âncora específica, ou CLI/MCP divergirem, a opção A é refutada."
out_of_scope:
  - collector live de Kafka, MSK, Kinesis ou CloudWatch
  - regra de hot partition, custo, throughput ou capacidade sem série e baseline
  - compatibilidade completa de versões Kafka upstream/MSK
  - agentes especializados novos
unknowns: [U1, U2, U3, U4]
---

# STREAMING_TRANSPORT_DIAGNOSTICS — definição

Primeira especialização de transporte será observacional. O analyzer só
transforma dumps já presentes em facts determinísticos; julgamento e collectors
ficam para ondas posteriores quando houver evidência e contratos estáveis.
