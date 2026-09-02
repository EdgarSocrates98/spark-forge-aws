# SparkForge AWS Copilot Instructions

This repository contains PySpark jobs designed for AWS Glue, Amazon S3, Parquet
and Apache Iceberg — and a deterministic diagnostic engine over them.

## Always

- detect Glue/Spark/Python/Iceberg versions before suggesting an API or setting;
- inspect execution plans and metrics before tuning;
- prioritize reducing scans, cardinality and shuffle before adding workers;
- prefer native Spark functions over Python UDFs;
- preserve correctness and validate outputs (counts, schema, keys, aggregates);
- include evidence, expected effect as a hypothesis, risks, validation and
  rollback in every recommendation;
- avoid `collect`, `toPandas`, `coalesce(1)`, arbitrary `repartition` and
  indiscriminate `cache`;
- distinguish Parquet file layout from Iceberg metadata maintenance;
- never propose destructive Iceberg maintenance without explicit retention and
  scope confirmation.

## Use the engine instead of reading by eye

The CLI answers most questions without anyone opening a file. Copilot has no MCP
here, so **use the CLI** — every MCP tool has a CLI verb with the same contract:

| Question | Command |
|---|---|
| where is X defined | `sparkforge code search <term>` |
| who calls X, what breaks if I change it | `sparkforge code symbol <node_id>` |
| **how** does X reach Y | `sparkforge code path <origin> <target>` |
| how is this code organized | `sparkforge code shape` |
| the context pack within a byte budget | `sparkforge code context "<task>"` |
| source, labelled as untrusted content | `sparkforge code read <node_id>` |
| is the index fresh | `sparkforge code status` / `code sync` |
| judge artifacts against the rule catalog | `sparkforge analyze ...` then `sparkforge judge` |

## Economy: measure before claiming a saving

**68 tools, 31 accept `detail_level`** (`summary`, `normal`, `full`). Pass
`--detail-level summary` when you only need the verdict.

**Read the number before claiming a reduction.** Measured 2026-09-02: `summary`
against `full` is **1.3%** on the retrieval gold set, because the pack's fixed
envelope (840 bytes) dominates a small corpus.

**The denominator decides the sign.** Against reading the files the index saves
**649.5x**; against a `grep` by name, **9.4x**; against a surgical `grep` by
definition it **costs 5.3x more**. Publish the denominator with the ratio, or the
number means nothing.

**A pack that omitted the required symbol is a failure, not a saving.**
`python scripts/check_recall_economy.py` enforces that: recall by name has a hard
100% floor.

## Three states, never two

Observed, unknown, and not applicable. Absence of evidence is never evidence of
absence — a missing artifact produces a named `*.unresolved` with the measurement
that would unblock it, never a silent zero and never a clean bill of health.

## Before opening a PR

See `docs/gates-por-mudanca.md` for which gate each kind of change touches. The
suite does not survive in a single process — run it in the nine batches defined
in `tests/test_suite_batches.py`.
