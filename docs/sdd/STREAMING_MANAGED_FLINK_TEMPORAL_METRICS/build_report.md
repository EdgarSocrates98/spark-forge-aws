---
sdd: 1
feature: STREAMING_MANAGED_FLINK_TEMPORAL_METRICS
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_MANAGED_FLINK_TEMPORAL_METRICS/plan.md
  sha256: "7de61b8da0b62df487d28a65b38402ed5966a55026e24c2b6be938bfe04ffe10"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_are_collected_and_normalized -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-temporal-t1-red", exit: 1}
    green: {command: "python -m pytest tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_are_collected_and_normalized -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-temporal-t1-green2", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_feed_analyzer -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-temporal-t2-green", exit: 1}
    green: {command: "python -m pytest tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_feed_analyzer -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-temporal-t2-green2", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_collect_managed_flink.py::test_cli_and_mcp_managed_flink_temporal_collection_match -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-temporal-t3-red", exit: 1}
    green: {command: "python -m pytest tests/test_collect_managed_flink.py::test_cli_and_mcp_managed_flink_temporal_collection_match -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-temporal-t3-green", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_collect_managed_flink.py::test_managed_flink_temporal_docs_state_window_and_limits -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-temporal-t4-red", exit: 1}
    green: {command: "python -m pytest tests/test_collect_managed_flink.py::test_managed_flink_temporal_docs_state_window_and_limits -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-temporal-t4-docs2", exit: 0}
claims:
  - text: "O collector consulta exatamente cinco métricas application-level do Managed Flink, normaliza observações timestamped e preserva missing/unresolved sem preencher zero."
    evidence_ref: "tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_are_collected_and_normalized"
  - text: "O artifact temporal alimenta managed_flink.metric com unidade, estatística e observed_at, mantendo unresolved e sem emitir flink.application."
    evidence_ref: "tests/test_collect_managed_flink.py::test_managed_flink_temporal_metrics_feed_analyzer"
  - text: "A repetição do mesmo artifact temporal é cache hit e não chama AWS novamente."
    evidence_ref: "tests/test_collect_managed_flink.py::test_managed_flink_temporal_cache_is_offline"
  - text: "CLI e MCP propagam a mesma janela temporal e produzem envelope equivalente sem adicionar tool."
    evidence_ref: "tests/test_collect_managed_flink.py::test_cli_and_mcp_managed_flink_temporal_collection_match"
  - text: "Knowledge, guias, referências, coverage, locks e contadores registram janela, métricas e limites."
    evidence_ref: "tests/test_collect_managed_flink.py::test_managed_flink_temporal_docs_state_window_and_limits"
change_id: null
---

# STREAMING_MANAGED_FLINK_TEMPORAL_METRICS — relatório do build

## Resultado

Build concluído em T1–T4. A feature reutiliza o collector Managed Flink
existente e permanece read-only/offline-first: `DescribeApplication` preserva
configuração observada, enquanto a janela opcional usa `get_metric_data` do
CloudWatch para cinco métricas de aplicação. O analyzer consome o envelope
normalizado; julgamento de saúde, causa, SLO, custo e performance continua fora.

## Desvios e decisões durante o build

- O SDD inicialmente classificava AC3 como guarda porque facts `metric` genéricos
  já existiam. A execução mostrou uma mudança real no formato do artifact:
  `metrics.observations` precisava ser descompactado; AC3 foi corrigida e o
  vermelho observado foi preservado.
- A superfície não ganhou tool nova. CLI, MCP e arquivo continuam portas do
  mesmo collector, com os parâmetros opcionais da janela.
- O teste de cache temporal foi acrescentado para fechar a previsão de cache do
  define; o cache existente passou sem segunda chamada AWS.
- A suíte completa não foi executada. Foi usado `python -m pytest tests/ --collect-only -q`
  para atualizar a contagem de **14492** testes e somente gates focados para
  execução.

## Revisão

Revisão manual de especificação: T1 cobre exatamente as cinco métricas, janela,
paginação, missing e redaction; T2 preserva o handoff para `managed_flink.*`;
T3 mantém paridade; T4 fecha documentação e locks. Revisão manual de qualidade:
limites são explícitos, ausência permanece `unresolved`, cache é offline-first,
nenhuma escrita AWS foi adicionada e não há claim de saúde, custo ou ganho.
