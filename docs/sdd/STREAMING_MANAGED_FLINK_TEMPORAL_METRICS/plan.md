---
sdd: 1
feature: STREAMING_MANAGED_FLINK_TEMPORAL_METRICS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_MANAGED_FLINK_TEMPORAL_METRICS/design.md
  sha256: "783091539e9e4393596f5bb0ca85cb8d9775790d4e1d88cbcfecccbb75dcbe45"
tasks:
  - id: T1
    files: [tests/test_collect_managed_flink.py, sparkforge/collect/managed_flink.py]
    covers: [AC1, AC2]
    test: {path: tests/test_collect_managed_flink.py, name: test_managed_flink_temporal_metrics_are_collected_and_normalized}
  - id: T2
    files: [tests/test_collect_managed_flink.py]
    covers: [AC3]
    test: {path: tests/test_collect_managed_flink.py, name: test_managed_flink_temporal_metrics_feed_analyzer}
  - id: T3
    files: [tests/test_collect_managed_flink.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, parity.yaml, manifest.json]
    covers: [AC4]
    test: {path: tests/test_collect_managed_flink.py, name: test_cli_and_mcp_managed_flink_temporal_collection_match}
  - id: T4
    files: [tests/test_collect_managed_flink.py, knowledge/flink-streaming.md, knowledge/transport-diagnostics.md, knowledge/streaming/runtime-matrix.md, docs/guia/03-cli.md, docs/guia/04-mcp.md, docs/guia/referencia/tools/sparkforge_collect_managed_flink.md, docs/streaming/prompt-coverage.md, docs/DELIVERY-LEDGER.md, docs/EVOLUTION-CURRENT.md, docs/superpowers/STATUS.md, docs/surface.lock.json, knowledge/sources.lock.json, knowledge/offline-manifest.json]
    covers: [AC5]
    test: {path: tests/test_collect_managed_flink.py, name: test_managed_flink_temporal_docs_state_window_and_limits}
---

# STREAMING_MANAGED_FLINK_TEMPORAL_METRICS — plano

Implementação serializada em TDD. Cada tarefa começa com teste vermelho, aplica
uma mudança primária e repete o mesmo teste verde. O collector não cria nova
tool: apenas amplia os parâmetros declarados de
`sparkforge_collect_managed_flink`.

## T1 — CloudWatch application-level

Adicionar fake CloudWatch, validação ISO/período, query única com cinco
métricas, dimensão `Application`, paginação limitada, normalização de
timestamps, missing/status/unresolved e path que inclui janela. Rodar o teste
AC1/AC2 vermelho antes do collector e verde depois.

## T2 — analyzer temporal (guarda de regressão)

Alimentar o artifact coletado no analyzer `managed_flink`, confirmando que as
observações normalizadas viram `managed_flink.metric` com unidade, estatística e
`observed_at`, sem alterar fatos `flink.*`. Como o extrator já aceitava facts
metric genéricos antes desta feature, a tarefa é uma guarda que passa antes e
depois da mudança; rodar o teste e registrar a execução verde.

## T3 — CLI/MCP

Propagar `metrics_start`, `metrics_end` e `metrics_period` por core, CLI e
schema MCP; atualizar paridade e manifesto mantendo o número de tools. Rodar
paridade AC4 e regenerar referências.

## T4 — knowledge e gates

Atualizar knowledge, guias, coverage, fontes e locks. Rodar testes focados,
`gen_reference_docs --check`, surface lock, status numbers, bundle offline e
SDD check. Commit separado.
