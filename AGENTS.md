# Agent Instructions — SparkForge AWS

This repository contains reusable Agent Skills for AWS Glue PySpark performance engineering.

## Operating contract

- Establish a baseline before tuning.
- Diagnose the dominant bottleneck.
- Separate facts, evidence, hypotheses and recommendations.
- Do not invent performance gains.
- Change one primary variable per benchmark.
- Validate data correctness after every optimization.
- Treat Glue, Spark and Iceberg versions as material constraints.
- Prefer algorithmic and data-layout improvements before scaling infrastructure.
- Provide rollback for production changes.

## Mandatory recommendation schema

```yaml
recommendation:
  title:
  severity:
  confidence:
  evidence: []
  root_cause:
  proposed_change: []
  expected_effect:
  risks: []
  tradeoffs: []
  validation: []
  rollback: []
```


## Advanced orchestration

For full/incremental AWS Glue workloads, start with `glue-incremental-performance-architect`. Build the call graph, classify the OOM, prove whether incremental runs still perform global work, and inspect Iceberg commit/file/metadata behavior before infrastructure tuning.
