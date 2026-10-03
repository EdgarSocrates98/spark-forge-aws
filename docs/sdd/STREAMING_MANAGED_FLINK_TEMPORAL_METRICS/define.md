---
sdd: 1
feature: STREAMING_MANAGED_FLINK_TEMPORAL_METRICS
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Uma janela CloudWatch opcional no collector Managed Flink transforma métricas de aplicação observadas em facts temporais sem inferir zero, causa ou saúde."
  prediction: "Com start/end explícitos, o artifact preserva cinco queries AWS/KinesisAnalytics, resultados, timestamps, unidades e métricas ausentes; o analyzer emite managed_flink.metric com observed_at e o cache não chama AWS novamente."
  experiment: "Executar o collector com clientes falsos KinesisAnalytics v2 e CloudWatch, analisar o artifact como managed_flink e repetir a coleta a partir do cache."
acceptance:
  - id: AC1
    statement: "A coleta temporal usa somente cloudwatch.get_metric_data, exige janela timezone-aware válida, limita período/paginação e consulta exatamente cinco métricas de aplicação com dimensão Application."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_are_collected_and_normalized"}
  - id: AC2
    statement: "O artifact registra namespace, start/end/period, query definitions, resultados e missing metrics sem converter ausência em zero ou esconder status inválido."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_are_collected_and_normalized"}
  - id: AC3
    statement: "O analyzer consome observações temporais e preserva managed_flink.metric, unidade, estatística e observed_at."
    guard: "O extrator managed_flink já preservava registros metric genéricos; este teste impede que a nova forma temporal quebre essa integração."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_feed_analyzer"}
  - id: AC4
    statement: "CLI e MCP do collector existente propagam a janela temporal com paridade de artifact e sem aumentar a quantidade de tools."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_cli_and_mcp_managed_flink_temporal_collection_match"}
  - id: AC5
    statement: "Knowledge, guias, referências, locks, coverage e SDD registram as métricas, janela e limites e passam nos gates distribuídos."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_managed_flink_temporal_docs_state_window_and_limits"}
success:
  - id: SC1
    metric: "AC1–AC5 verdes; ausência, status parcial e shape inválido permanecem missing/unresolved"
    source: "testes com clientes falsos, analyzer offline e gates de distribuição"
out_of_scope:
  - "métricas Task/Operator/Parallelism, custom metrics e connector-specific dimensions"
  - "job plan, savepoint, replay, benchmark e validação funcional"
  - "threshold universal, SLO, causa, custo atribuído ou estado live"
  - "qualquer chamada AWS de escrita"
unknowns:
  - id: U1
    blocks: [AC5]
    unlock: "Atualizar knowledge/offline-manifest, sources.lock, referências geradas e surface lock sem criar nova tool."
case_id: null
change_kinds: [extractor, tool_or_verb, knowledge_doc, status_numbers]
---

# STREAMING_MANAGED_FLINK_TEMPORAL_METRICS — requisitos

O collector continua ponte de aquisição; o julgamento permanece no analyzer
offline. A janela só existe quando o operador declara `start` e `end`, e a
ausência de série nunca vira zero.
