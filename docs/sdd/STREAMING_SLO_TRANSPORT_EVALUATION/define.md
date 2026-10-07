---
sdd: 1
feature: STREAMING_SLO_TRANSPORT_EVALUATION
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_TRANSPORT_EVALUATION/explore.md
  sha256: "d0408cbc3b2d687949d4f3e32351c314b038759513b068c3ed0a8efdb8004d58"
hypothesis:
  claim: "O compositor SLO existente consegue avaliar SLOs declarados de Kafka e Kinesis sem nova superfície quando recebe transport_key e facts temporais diretamente observados."
  prediction: "Uma série com pelo menos duas observações de kafka.lag ou kinesis.shard, identidade, unidade e janela compatíveis produz met ou violated; identidade, timestamp, métrica ou cobertura ausente produz somente streaming.slo.unresolved."
  experiment: "Extrair contrato, progress opcional e dump de transporte, executar mode=slo com transport_key, julgar goldens Kafka/Kinesis e comparar envelopes CLI/MCP."
acceptance:
  - id: AC1
    statement: "A avaliação escolhe um streaming.slo por nome/unicidade e, para source Kafka/Kinesis, exige transport_key declarado ou presente no contrato; query_name continua obrigatório somente para source Structured Streaming."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_evaluates_transport_slo_by_declared_identity}
  - id: AC2
    statement: "Kafka lag e Kinesis iterator age são métricas diretas com unidade canônica, timestamp timezone-aware, pelo menos duas observações e span que cobre a janela; status met/violated preserva os source_fact_ids."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_evaluates_kinesis_iterator_age_and_kafka_lag}
  - id: AC3
    statement: "Mistura de grupos/streams, ausência de transport_key, timestamp ou cobertura, métrica não observada e unidade incompatível produz unresolved nomeado e nunca met por ausência de evidência."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_transport_slo_unresolved_reasons}
  - id: AC4
    statement: "CLI e MCP passam transport_key ao mesmo core mode=slo e preservam envelopes compatíveis para Kafka/Kinesis sem adicionar tool."
    verified_by: {kind: test, ref: tests/test_analyze_streaming_composition.py::test_transport_slo_cli_and_mcp_envelopes_match}
  - id: AC5
    statement: "Goldens de Kafka met, Kinesis violated e identidade incompleta cobrem facts, avaliação, regras existentes e regressão dos modos anteriores."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens}
  - id: AC6
    statement: "Knowledge, skill, prompt coverage, referências, surface lock, manifests, mirrors e SDD registram SLO de transporte e seus limites."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "Todos AC1–AC6 verdes; Kafka/Kinesis separados por identidade e sem inferência de causa, custo ou saúde end-to-end."
    source: "pytest focalizado, goldens, judge, CLI/MCP e gates de superfície, documentação e bundle offline"
out_of_scope:
  - "CloudWatch live, p95/freshness/availability e métricas sem timestamp observado"
  - "Conversão de unidades, interpolação, agregação entre grupos/shards ou preenchimento de timestamps"
  - "FinOps, causalidade, benchmark, replay e validação funcional do consumidor"
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Confirmar a forma dos attrs timestamp/observed_at nos fatos kafka.lag e kinesis.shard antes do compositor."
  - id: U2
    blocks: [AC6]
    unlock: "Regenerar referências, surface lock, offline manifest e números correntes depois do encaminhamento de transport_key."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, agent_or_skill, status_numbers]
---

# STREAMING_SLO_TRANSPORT_EVALUATION — requisitos
