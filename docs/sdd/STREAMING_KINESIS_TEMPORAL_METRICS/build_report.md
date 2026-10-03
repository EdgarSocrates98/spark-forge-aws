---
sdd: 1
feature: STREAMING_KINESIS_TEMPORAL_METRICS
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_KINESIS_TEMPORAL_METRICS/plan.md
  sha256: "da4b5d33c1fd9bb0d66f346e9aa255d05597e5b2ffc7c4fdf6db13ec17d6a914"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_collect_streaming.py::test_kinesis_temporal_metrics_are_collected_and_normalized -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-red-t1", exit: 1}
    green: {command: "python -m pytest tests/test_collect_streaming.py::test_kinesis_temporal_metrics_are_collected_and_normalized -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-green-t1", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_collect_streaming.py::test_kinesis_temporal_metrics_feed_transport_analyzer -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-red-t2", exit: 1}
    green: {command: "python -m pytest tests/test_collect_streaming.py::test_kinesis_temporal_metrics_feed_transport_analyzer -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-green-t2", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_collect_streaming.py::test_cli_and_mcp_streaming_temporal_collection_match -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-red-t3", exit: 1}
    green: {command: "python -m pytest tests/test_collect_streaming.py::test_cli_and_mcp_streaming_temporal_collection_match -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-green-t3", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_collect_streaming.py::test_kinesis_temporal_docs_state_window_and_limits -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-green-t4", exit: 1}
    green: {command: "python -m pytest tests/test_collect_streaming.py::test_kinesis_temporal_docs_state_window_and_limits -q -p no:cacheprovider --basetemp=C:\\sf-test\\kinesis-temporal-green-t4b", exit: 0}
claims:
  - text: "O collector Kinesis consulta cinco métricas stream-level com janela e período bounded, preservando timestamps, unidade, estatística e lacunas."
    evidence_ref: "tests/test_collect_streaming.py::test_kinesis_temporal_metrics_are_collected_and_normalized"
  - text: "O artifact temporal alimenta fatos kinesis.metric sem acoplar o analyzer à resposta bruta do provider."
    evidence_ref: "tests/test_collect_streaming.py::test_kinesis_temporal_metrics_feed_transport_analyzer"
  - text: "CLI e MCP propagam a mesma janela e produzem artifact equivalente."
    evidence_ref: "tests/test_collect_streaming.py::test_cli_and_mcp_streaming_temporal_collection_match"
  - text: "Knowledge e guias deixam enhanced/shard-level, reshard history, KCL/EFO, replay e causalidade fora do contrato."
    evidence_ref: "tests/test_collect_streaming.py::test_kinesis_temporal_docs_state_window_and_limits"
change_id: null
---

# STREAMING_KINESIS_TEMPORAL_METRICS — relatório do build

## Desvios do plano

- A janela foi adicionada ao collector `streaming-integrations` existente; não
  foi criada tool, verbo ou namespace novo. O path inclui a janela somente no
  modo temporal, evitando colisão com o snapshot estrutural.
- O analyzer aceita o artifact composto e normaliza somente
  `kinesis.metrics.observations`; a resposta bruta do CloudWatch permanece no
  artifact e não entra no núcleo determinístico.
- `knowledge/sources.lock.json`, `knowledge/offline-manifest.json` e páginas de
  referência são derivados da documentação e do schema MCP atualizado.

## Revisão

Revisão de spec: conforme. Cada AC tem teste nomeado e todos os testes críticos
registraram red antes do verde. Revisão de qualidade: conforme; a coleta é
read-only, a janela é explícita, ausência não vira zero, métricas enhanced não
são habilitadas e nenhum threshold, causa, SLO, custo ou ganho é inferido.
