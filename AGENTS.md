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

## Coordinators and executors

Six coordinators live in `agents/*.md`, one per specialized angle of investigation. Each
declares `rule_areas`, the `skills` it draws on, and the five `executors` it dispatches
(`sf-inventory`, `sf-extractor`, `sf-judge`, `sf-verifier`, `sf-synthesizer` — one per
function of the phase loop, in `agents/executors/*.md`, each with an explicit `## Não faz`
negative boundary and a `## Pressupõe`/`## Entrega` handoff contract). A coordinator does
not execute: it reads the case, decides which executor runs next, and records in the case
which executor ran and with what result — same mechanism as skill tracking
(`sparkforge_case_update` with `skills_used`, executor name in place of skill name; see
`AGENT_PROTOCOL.md` rule 6).

| Coordinator | Use quando… | `rule_areas` |
|---|---|---|
| `spark-performance-architect` | diagnóstico geral de um job PySpark no Glue, gargalo dominante ainda não localizado | SF-PY, SF-UI, SF-PLAN |
| `glue-incremental-performance-architect` | fluxo full + incremental, latest-per-key em Iceberg bilionário, batching, OOM após horas | orquestra as demais áreas antes de tuning localizado |
| `glue-infra-reviewer` | gargalo ou risco na definição do job Glue, não no código — worker, auto scaling, bookmark, retries, Terraform | SF-GLUE, SF-ENV |
| `athena-query-optimizer` | custo ou latência na consulta Athena, não no job — bytes escaneados, pruning de partição, engine, workgroup | SF-ATH, SF-PQ |
| `pyspark-code-reviewer` | revisar código PySpark — PR, biblioteca ou job — correlacionando fonte, plano físico e call graph | SF-PY, SF-PLAN, SF-CG |
| `iceberg-performance-engineer` | dívida de data files, delete files, manifests, snapshots e manutenção de tabela Iceberg | SF-ICE, SF-PQ |

Which coordinator to use is data, not judgment: routes `AGENT-001`…`AGENT-006` in
`rules/catalog/routing.yaml` map the case's phase and dominant finding area to a
`recommended_agent`, and `sparkforge_next_step` / `sparkforge next-step` reads them —
never pick a coordinator by inspection.

On a platform without subagent dispatch (Devin, Codex, Copilot CI), `sparkforge playbook
<coordinator>` (CLI) or the `sparkforge_playbook` MCP tool returns the same decomposition
as a sequence of steps, reading the same `agents/` files a Claude Code coordinator would
dispatch as subagents: it loses the dispatch's parallelism, keeps the method.

## Deterministic evidence

Evidence for this project comes from deterministic extraction, not from an
LLM sampling the codebase. A `Fact` is an anchored observation — file, line,
symbol, snippet, or plan node — and it carries no judgment: no severity, no
threshold, no recommendation. A `Finding` is judgment, and it always carries a
non-empty `evidence` list of `fact_id` values plus a `rule_id` traceable to a
dated source in `rules/catalog/`. A `Finding` with empty evidence is invalid
by construction (see `sparkforge.findings.models.Finding.__post_init__`).

### What can be extracted

Thirteen extractors, all offline — they read artifacts already on disk and never
call AWS. Each has a CLI verb and an MCP tool with the same name:

| Artifact | CLI verb | Reads |
|---|---|---|
| PySpark source | `analyze pyspark` | `*.py` tree (AST) |
| Spark physical plan | `analyze plan` | pasted `explain("formatted")` output |
| Spark event log | `analyze event-log` | `*.jsonl` event log of a run |
| Iceberg metadata | `analyze iceberg` | dump of the metadata tables |
| Glue Data Catalog | `analyze catalog-schema` | `GetTables`/`GetTable` dump |
| Terraform | `analyze terraform` | `aws_glue_job` HCL |
| SQL | `analyze sql` | `*.sql` and `spark.sql(...)` literals |
| Athena workgroup | `analyze athena-workgroup` | `get_work_group` dump |
| Call graph | `analyze call-graph` | derived from PySpark facts |
| S3 object listing | `analyze s3-listing` | `s3api list-objects-v2` dump |
| Table consumers | `analyze consumers` | declared inventory, versioned in the repo |
| Terraform change | `analyze terraform-diff` | two states of the same module |
| Runtime | `runtime detect` | every source above, cross-checked |
| Correlation | `fuse` | facts from several extractors at once |

Collection of the raw artifacts (`collect *`) requires boto3 and credentials
and is the only part that touches AWS. The core never imports boto3 or the MCP
SDK, so the CLI and the file-only path work without either.

### Three states, never two

The hardest rule in this codebase, and the one worth stating in every report:
**absence of evidence is not evidence of absence.** When an artifact does not
answer a question, the extractor emits an `*.unresolved` fact naming the blind
spot, and the rule that depended on it does not fire. Empty `PartitionFilters`
in a plan does not prove the table is partitioned; an interpolated Terraform
value does not prove the argument is unset; an unparseable Athena engine
version does not mean version zero. Report the blind spot; never fill it in.

### Version guard

Every rule declares `runtime_scope`, and the engine skips it when the detected
runtime is out of range — so state the detected runtime before any finding.
Divergence between sources is never resolved by picking one: it is `SF-ENV-001`
at P0, because every threshold downstream is evaluated against the wrong
runtime until it is settled. See `knowledge/glue/runtime-matrix.md` for the
Glue 4.0 / 5.0 / 5.1 matrix and the Iceberg V3 versus Athena trap in Glue 5.1.

The `recommendation:` schema documented above remains valid: `Finding` is a
compatible superset of it, with the same fields (`title`, `severity`,
`evidence`, `proposed_change`/`expected_effect`, `risks`, `tradeoffs`,
`validation`, `rollback`) plus the anchoring (`subject`, `rule_id`,
`sources`) that makes each field traceable rather than asserted.

See `AGENT_PROTOCOL.md` for the operating rules every skill and agent are
injected with, and `docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md`
for the full Fact/Finding contract.
