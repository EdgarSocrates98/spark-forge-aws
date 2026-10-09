---
sdd: 1
feature: STREAMING_KINESIS_TEMPORAL_METRICS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_KINESIS_TEMPORAL_METRICS/explore.md
  sha256: "8bcb92589033198d54658b225438951130f8092809dd5761772c32cfc96c9721"
hypothesis:
  claim: "Uma janela CloudWatch opcional no collector Kinesis transforma métricas stream-level observadas em facts temporais sem inferir zero, causa ou saúde."
  prediction: "Com start/end explícitos, o artifact preserva queries, resultados, timestamps, unidades e missing metrics; o analyzer emite kinesis.metric com observed_at e o cache não chama AWS novamente."
  experiment: "Executar collector com fake Kinesis/CloudWatch, analisar o artifact como transporte Kinesis e repetir a coleta a partir do cache."
acceptance:
  - id: AC1
    statement: "A coleta temporal usa somente cloudwatch.get_metric_data, exige janela válida, limita período/paginação e consulta exatamente cinco métricas stream-level com dimensão StreamName."
    verified_by: {kind: test, ref: "tests/test_collect_streaming.py::test_kinesis_temporal_metrics_are_collected_and_normalized"}
  - id: AC2
    statement: "O artifact registra start/end/period, query definitions, resultados e missing metrics sem converter ausência em zero."
    verified_by: {kind: test, ref: "tests/test_collect_streaming.py::test_kinesis_temporal_metrics_are_collected_and_normalized"}
  - id: AC3
    statement: "O analyzer consome observações temporais e preserva kinesis.metric, unidade e observed_at."
    verified_by: {kind: test, ref: "tests/test_collect_streaming.py::test_kinesis_temporal_metrics_feed_transport_analyzer"}
  - id: AC4
    statement: "CLI e MCP do collector existente propagam a janela sem alterar a quantidade de tools."
    verified_by: {kind: test, ref: "tests/test_collect_streaming.py::test_cli_and_mcp_streaming_temporal_collection_match"}
  - id: AC5
    statement: "Knowledge, guias, referências, locks e SDD registram o limite stream-level e passam nos gates."
    verified_by: {kind: test, ref: "tests/test_collect_streaming.py::test_kinesis_temporal_docs_state_window_and_limits"}
success:
  - id: SC1
    metric: "AC1–AC5 verdes; ausência de métrica permanece missing/unresolved"
    source: "testes com clientes falsos, analyzer offline e gates de distribuição"
out_of_scope:
  - "métricas shard-level/enhanced monitoring"
  - "MSK CloudWatch metrics, Kafka Connect REST, replay e benchmark"
  - "threshold universal, causa, custo atribuído ou estado live"
  - "qualquer chamada AWS de escrita"
unknowns:
  - id: U1
    blocks: [AC5]
    unlock: "Atualizar knowledge/offline-manifest, sources.lock, referências geradas e surface lock sem criar nova tool."
case_id: null
change_kinds: [extractor, tool_or_verb, knowledge_doc, status_numbers]
---

# STREAMING_KINESIS_TEMPORAL_METRICS — requisitos

O collector continua ponte de aquisição; o julgamento permanece no analyzer
offline. A janela só existe quando o operador declara `start` e `end`, e a
ausência de série nunca vira zero.
