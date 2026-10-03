---
sdd: 1
feature: STREAMING_KINESIS_TEMPORAL_METRICS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_KINESIS_TEMPORAL_METRICS/design.md
  sha256: "0afa43ec783657446435582642609ca9ad9b5f166fafdc0cd08faf375672d62e"
tasks:
  - id: T1
    files: [tests/test_collect_streaming.py, sparkforge/collect/streaming.py]
    covers: [AC1, AC2]
    test: {path: tests/test_collect_streaming.py, name: test_kinesis_temporal_metrics_are_collected_and_normalized}
  - id: T2
    files: [tests/test_collect_streaming.py, sparkforge/facts/transport.py]
    covers: [AC3]
    test: {path: tests/test_collect_streaming.py, name: test_kinesis_temporal_metrics_feed_transport_analyzer}
  - id: T3
    files: [tests/test_collect_streaming.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py]
    covers: [AC4]
    test: {path: tests/test_collect_streaming.py, name: test_cli_and_mcp_streaming_temporal_collection_match}
  - id: T4
    files: [tests/test_collect_streaming.py, knowledge/transport-diagnostics.md, knowledge/streaming-integrations.md, docs/guia/03-cli.md, docs/guia/04-mcp.md, docs/streaming/prompt-coverage.md]
    covers: [AC5]
    test: {path: tests/test_collect_streaming.py, name: test_kinesis_temporal_docs_state_window_and_limits}
---

# STREAMING_KINESIS_TEMPORAL_METRICS — plano

Implementação serializada em TDD. Cada tarefa começa com teste vermelho, aplica
uma mudança primária e repete o mesmo teste verde. O collector não cria nova
tool: apenas amplia parâmetros declarados de `sparkforge_collect_streaming_integrations`.

## T1 — CloudWatch stream-level

Adicionar fake `cloudwatch.get_metric_data`, validação ISO/período, query única
com cinco métricas, paginação limitada, normalização de timestamps e path que
inclui janela. Red/green no teste AC1.

## T2 — analyzer temporal

Adicionar `kinesis.metrics.observations` ao contrato e converter cada par
timestamp/valor em `kinesis.metric`; missing/status parcial vira unresolved,
nunca zero. Red/green no teste AC3.

## T3 — CLI/MCP

Propagar `metrics_start`, `metrics_end` e `metrics_period` por core, CLI e
schema MCP. Regerar referências; o número de tools deve permanecer 136.

## T4 — knowledge e gates

Atualizar knowledge, guias, prompt coverage, sources/manifest e referências.
Rodar testes focados, `gen_reference_docs --check`, surface lock, status
numbers, bundle offline e SDD check. Commit separado.
