---
sdd: 1
feature: STREAMING_KINESIS_TEMPORAL_METRICS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_KINESIS_TEMPORAL_METRICS/define.md
  sha256: "9168a681ff86b0114854e98ef6bd017a2e059931e2b82411691780af814f053f"
files:
  - {path: tests/test_collect_streaming.py, action: modify, reason: "fake CloudWatch, janela, cache, analyzer, CLI/MCP e documentação"}
  - {path: sparkforge/collect/streaming.py, action: modify, reason: "queries AWS/Kinesis stream-level, normalização, paginação e cache por janela"}
  - {path: sparkforge/facts/transport.py, action: modify, reason: "consumir observations CloudWatch como kinesis.metric temporal"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "propagar janela para collector existente"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "expor start/end/period opcionais no verbo existente"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "declarar parâmetros no schema MCP sem nova tool"}
  - {path: knowledge/transport-diagnostics.md, action: modify, reason: "documentar série Kinesis stream-level, retenção e limites"}
  - {path: knowledge/streaming-integrations.md, action: modify, reason: "documentar comando e unresolved temporal"}
  - {path: docs/guia/03-cli.md, action: modify, reason: "documentar coleta temporal Kinesis"}
  - {path: docs/guia/04-mcp.md, action: modify, reason: "documentar parâmetros temporais da tool existente"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "reduzir lacuna explícita de Kinesis"}
  - {path: docs/sdd/STREAMING_KINESIS_TEMPORAL_METRICS/build_report.md, action: create, reason: "evidência TDD e gates"}
  - {path: docs/sdd/STREAMING_KINESIS_TEMPORAL_METRICS/ship.md, action: create, reason: "fechamento do contrato"}
decisions:
  - id: D1
    choice: "Reutilizar collect streaming-integrations e incluir a janela somente no path quando métricas forem solicitadas."
    rejected: ["tool nova, que aumentaria surface e custo de contexto sem novo objetivo do usuário"]
    rollback: "git revert dos commits da feature; snapshot Kinesis anterior continua sem série temporal."
  - id: D2
    choice: "Consultar cinco métricas stream-level em uma chamada GetMetricData paginável."
    rejected: ["shard-level por padrão, que exigiria enhanced monitoring e custo adicional", "thresholds no collector, que confundiriam evidência com julgamento"]
    rollback: "Remover apenas a seção metrics do artifact e manter as funções de snapshot."
  - id: D3
    choice: "Persistir observations normalizadas além do resultado AWS para alimentar facts com timestamp textual."
    rejected: ["fazer o extrator interpretar toda a forma boto3 diretamente, que acoplaria facts ao provider"]
    rollback: "Ignorar observations e retornar unresolved temporal; o raw result permanece auditável."
covers:
  - {part: collector, acceptance: [AC1, AC2]}
  - {part: analyzer, acceptance: [AC3]}
  - {part: adapters, acceptance: [AC4]}
  - {part: documentation, acceptance: [AC5]}
---

# STREAMING_KINESIS_TEMPORAL_METRICS — desenho

## Fluxo

`collect streaming-integrations --kinesis-stream ... --metrics-start ...
--metrics-end ...` → `AWS/Kinesis GetMetricData` → artifact composto com
`kinesis.metrics.observations` → `analyze transport --artifact kinesis` →
`kinesis.metric`/`kinesis.unresolved`.

## Conhecimento consultado

- `knowledge/transport-diagnostics.md`, lido como contrato local de transporte.
- AWS Kinesis CloudWatch monitoring:
  `https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html`.
- AWS CloudWatch `GetMetricData`:
  `https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/metrics-classic-getdata.html`.
- Boto3 `get_metric_data`:
  `https://docs.aws.amazon.com/boto3/latest/reference/services/cloudwatch/client/get_metric_data.html`.
