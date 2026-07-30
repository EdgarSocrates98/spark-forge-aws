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

## Deterministic evidence (Fase 0)

Evidence for this project comes from deterministic extraction, not from an
LLM sampling the codebase. A `Fact` is an anchored observation — file, line,
symbol, snippet — produced by static AST analysis, and it carries no
judgment: no severity, no threshold, no recommendation. A `Finding` is
judgment, and it always carries a non-empty `evidence` list of `fact_id`
values plus a `rule_id` traceable to a dated source in `rules/catalog/`. A
`Finding` with empty evidence is invalid by construction (see
`sparkforge.findings.models.Finding.__post_init__`).

The `recommendation:` schema documented above remains valid: `Finding` is a
compatible superset of it, with the same fields (`title`, `severity`,
`evidence`, `proposed_change`/`expected_effect`, `risks`, `tradeoffs`,
`validation`, `rollback`) plus the anchoring (`subject`, `rule_id`,
`sources`) that makes each field traceable rather than asserted.

See `AGENT_PROTOCOL.md` for the operating rules every skill and agent are
injected with, and `docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md`
for the full Fact/Finding contract.
