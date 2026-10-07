---
sdd: 1
feature: STREAMING_MANAGED_FLINK_COLLECTOR
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_MANAGED_FLINK_COLLECTOR/plan.md
  sha256: "b5f566cf9d004c73090c30da24961e185942595fbd327f152b88f44a08e2fdc6"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_collect_managed_flink.py::test_collector_normalizes_describe_response tests/test_collect_managed_flink.py::test_collector_cache_is_offline_and_manifested -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-red-t1", exit: 2}
    green: {command: "python -m pytest tests/test_collect_managed_flink.py::test_collector_normalizes_describe_response tests/test_collect_managed_flink.py::test_collector_cache_is_offline_and_manifested -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-green-t1", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_collect_managed_flink.py::test_cli_and_mcp_managed_flink_collection_match -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-red-t2", exit: 1}
    green: {command: "python -m pytest tests/test_collect_managed_flink.py::test_cli_and_mcp_managed_flink_collection_match -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-green-t2", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_collect_managed_flink.py::test_collected_artifact_feeds_managed_flink_analyzer -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-red-t3", exit: 1}
    green: {command: "python -m pytest tests/test_collect_managed_flink.py::test_collected_artifact_feeds_managed_flink_analyzer -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-green-t3", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_collect_managed_flink.py::test_managed_flink_collection_docs_state_read_only_limits -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-red-t4", exit: 1}
    green: {command: "python -m pytest tests/test_collect_managed_flink.py::test_managed_flink_collection_docs_state_read_only_limits -q -p no:cacheprovider --basetemp=C:\\sf-test\\managed-flink-green-t4", exit: 0}
claims:
  - text: "O collector normaliza DescribeApplication, redige campos secret-like, preserva unresolved e usa cache offline-first."
    evidence_ref: "tests/test_collect_managed_flink.py::test_collector_normalizes_describe_response"
  - text: "CLI e MCP produzem o mesmo envelope de coleta Managed Flink."
    evidence_ref: "tests/test_collect_managed_flink.py::test_cli_and_mcp_managed_flink_collection_match"
  - text: "O artifact coletado alimenta managed_flink.* e preserva application_version_id sem misturar flink.*."
    evidence_ref: "tests/test_collect_managed_flink.py::test_collected_artifact_feeds_managed_flink_analyzer"
  - text: "Guias e knowledge declaram read-only, limites e métricas ausentes como unresolved."
    evidence_ref: "tests/test_collect_managed_flink.py::test_managed_flink_collection_docs_state_read_only_limits"
change_id: null
---

# STREAMING_MANAGED_FLINK_COLLECTOR — relatório do build

## Desvios do plano

- O normalizador também preserva `application_version_id`, `service_execution_role`
  e `application_mode` no fact `managed_flink.application`, porque esses campos
  são parte da identidade observada e estavam disponíveis no mesmo artifact.
- A regeneração acrescentou `knowledge/offline-manifest.json`,
  `knowledge/sources.lock.json` e páginas de referência geradas; são registros
  derivados da mesma mudança, sem nova superfície além da tool declarada.

## Revisão

Revisão de spec: conforme. Cada AC tem teste nomeado e os testes críticos
registraram red antes do verde. Revisão de qualidade: conforme; collector não
chama mutações AWS, não copia `TextContent`/secret-like e o namespace
`managed_flink` permanece separado do Flink upstream.
