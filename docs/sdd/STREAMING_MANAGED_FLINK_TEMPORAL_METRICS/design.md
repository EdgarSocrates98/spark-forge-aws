---
sdd: 1
feature: STREAMING_MANAGED_FLINK_TEMPORAL_METRICS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_MANAGED_FLINK_TEMPORAL_METRICS/define.md
  sha256: "65614c6dee8f20fa91ba8297472acf98a335b193fdd00c87b6255c75f0faa03f"
files:
  - {path: tests/test_collect_managed_flink.py, action: modify, reason: "fake clients, temporal window, cache, analyzer, parity and documentation contract"}
  - {path: sparkforge/collect/managed_flink.py, action: modify, reason: "AWS/KinesisAnalytics temporal queries, normalization, bounded pagination and cache path"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "propagate temporal window through existing collector"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "expose optional start/end/period on collect managed-flink"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "declare temporal parameters in existing MCP schema and handler"}
  - {path: parity.yaml, action: modify, reason: "keep CLI/MCP/file parity contract current"}
  - {path: manifest.json, action: modify, reason: "refresh generated surface manifest without adding a tool"}
  - {path: knowledge/flink-streaming.md, action: modify, reason: "document official Managed Flink CloudWatch metrics and unresolved limits"}
  - {path: knowledge/transport-diagnostics.md, action: modify, reason: "document temporal CloudWatch artifact boundary"}
  - {path: knowledge/streaming/runtime-matrix.md, action: modify, reason: "reduce Managed Flink temporal evidence gap"}
  - {path: docs/guia/03-cli.md, action: modify, reason: "document temporal Managed Flink command"}
  - {path: docs/guia/04-mcp.md, action: modify, reason: "document parameters and limits of existing tool"}
  - {path: docs/guia/referencia/tools/sparkforge_collect_managed_flink.md, action: modify, reason: "regenerate MCP reference"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "record bounded Managed Flink temporal coverage and remaining gaps"}
  - {path: docs/DELIVERY-LEDGER.md, action: modify, reason: "record feature and evidence"}
  - {path: docs/EVOLUTION-CURRENT.md, action: modify, reason: "record current streaming capability"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "update current delivery numbers"}
  - {path: docs/surface.lock.json, action: modify, reason: "refresh measured surface bytes"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "register official Managed Flink metrics and CloudWatch API sources"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "refresh hashes of changed knowledge documents"}
  - {path: docs/sdd/STREAMING_MANAGED_FLINK_TEMPORAL_METRICS/build_report.md, action: create, reason: "TDD evidence and gates"}
  - {path: docs/sdd/STREAMING_MANAGED_FLINK_TEMPORAL_METRICS/ship.md, action: create, reason: "closure of temporal Managed Flink contract"}
decisions:
  - id: D1
    choice: "Reuse collect managed-flink and include the temporal section only when start/end are declared."
    rejected: ["new tool, which would increase surface and context cost without a second objective"]
    rollback: "git revert the feature commits; the previous DescribeApplication artifact remains valid."
  - id: D2
    choice: "Query five application-level metrics in one paginable GetMetricData request: cpuUtilization, heapMemoryUtilization, lastCheckpointDuration, lastCheckpointSize and numberOfFailedCheckpoints."
    rejected: ["Task/Operator/Parallelism by default, which would multiply dimensions and cost", "thresholds in the collector, which would mix evidence with judgment", "deprecated uptime/downtime, which would make runtime interpretation version-sensitive"]
    rollback: "Remove only the metrics section from the artifact and retain the configuration snapshot."
  - id: D3
    choice: "Persist normalized observations beside raw MetricDataResults so facts stay provider-independent and timestamped."
    rejected: ["make the fact extractor parse the entire boto3 response, which would couple facts to provider shape"]
    rollback: "Ignore observations and return the declared unresolved temporal gap; raw results remain auditable."
covers:
  - {part: collector, acceptance: [AC1, AC2]}
  - {part: analyzer, acceptance: [AC3]}
  - {part: adapters, acceptance: [AC4]}
  - {part: documentation, acceptance: [AC5]}
---

# STREAMING_MANAGED_FLINK_TEMPORAL_METRICS — desenho

## Fluxo

`collect managed-flink --application-name ... --metrics-start ...
--metrics-end ...` → `AWS/KinesisAnalytics GetMetricData` → artifact com
`managed_flink.metrics.observations` → `analyze flink --artifact managed_flink`
→ `managed_flink.metric`/`managed_flink.unresolved`.

## Conhecimento consultado

- `knowledge/flink-streaming.md`, lido como contrato local de Managed Flink.
- AWS Metrics and dimensions in Managed Service for Apache Flink:
  `https://docs.aws.amazon.com/managed-flink/latest/java/metrics-dimensions.html`.
- AWS View CloudWatch metrics:
  `https://docs.aws.amazon.com/managed-flink/latest/java/metrics-dimensions-viewing.html`.
- Boto3 `get_metric_data`:
  `https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/get_metric_data.html`.
