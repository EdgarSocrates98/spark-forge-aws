# Agent Instructions — SparkForge AWS

This repository contains reusable Agent Skills for PySpark data engineering on AWS —
performance on AWS Glue and on Amazon EMR on EC2, plus the placement and cost of data
validation inside the job.

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

Eight coordinators live in `agents/*.md`, one per specialized angle of investigation. Each
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
| `spark-performance-architect` | diagnóstico geral de um job PySpark no Glue, gargalo dominante ainda não localizado; e comprovar o ganho de uma mudança comparando dois runs | SF-PY, SF-UI, SF-PLAN, SF-BENCH |
| `glue-incremental-performance-architect` | fluxo full + incremental, latest-per-key em Iceberg bilionário, batching, OOM após horas | orquestra as demais áreas antes de tuning localizado |
| `glue-infra-reviewer` | gargalo ou risco na definição do job Glue, não no código — worker, auto scaling, bookmark, retries, Terraform | SF-GLUE, SF-ENV |
| `athena-query-optimizer` | custo ou latência na consulta Athena, não no job — bytes escaneados, pruning de partição, engine, workgroup | SF-ATH, SF-PQ |
| `pyspark-code-reviewer` | revisar código PySpark — PR, biblioteca ou job — correlacionando fonte, plano físico e call graph | SF-PY, SF-PLAN, SF-CG |
| `iceberg-performance-engineer` | dívida de data files, delete files, manifests, snapshots e manutenção de tabela Iceberg | SF-ICE, SF-PQ |
| `emr-infra-reviewer` | risco na definição de um cluster Amazon EMR on EC2 — fleets/groups, Spot por papel, managed scaling, Configurations em dois níveis, LogUri | SF-EMR, SF-ENV |
| `data-quality-reviewer` | o job valida dado e a pergunta é se a validação está no lugar certo, se ela tem consequência e quanto custa — não se o dado está correto | SF-DQ |

Which coordinator to use is data, not judgment: routes `AGENT-001`…`AGENT-008` in
`rules/catalog/routing.yaml` map the case's phase and dominant finding area to a
`recommended_agent`, and `sparkforge_next_step` / `sparkforge next-step` reads them —
never pick a coordinator by inspection.

**Three platforms dispatch.** Claude Code (the `Agent` tool of this CLI), the **Devin CLI**,
and the **Devin Local agent** of Devin Desktop (behind the *Subagents (Preview)* toggle).
Devin reads custom subagent profiles from `.agents/agents/` natively and imports
`.claude/agents/*.md` — both directories are generated mirrors of `agents/`, so the **eight
coordinators** are subagent profiles there without any per-platform authoring. **The five
executors are not at a documented discovery layout**, and this is measurement, not
assumption: the source describes two layouts, flat `agents/<name>.md` and directory
`agents/<name>/AGENT.md`, and the Claude Code import pattern `.claude/agents/*.md` is
flat. `executors/sf-judge.md` is neither — `executors/` would only publish a profile named
`executors`, and only if it held an `AGENT.md`. Whether the scan recurses is undocumented,
the same ambiguity as the repository-root `agents/` (V-DV-7), and the same rule applies:
do not presume. Nothing is lost — `sparkforge playbook <coordinator>` reads
`agents/executors/` from the repository itself and returns the same five steps on every
platform, needing no discovery at all.

**A coordinator dispatched as a subagent does not dispatch the five executors.** By
default *"subagents cannot spawn their own subagents — only the root agent can"*, and
`run_subagent`/`read_subagent` are removed inside one; the `max-nesting` field that would
opt back in is declared in no profile here. Dispatching a coordinator on Devin buys its
**method**, not its fan-out — the decomposition runs inline, which is what `playbook`
returns. The
`.agents/` mirror is **rendered**, not copied: it drops `tools:` (the value mapping from
Claude Code's field to Devin's tool names is undocumented, and guessing in a permission
field grants or denies wrongly) and never gains `model:` (the subagent model resolves
through a router at spawn time and an org admin overrides it). **Dropping `tools:` is not
a security boundary, and could not be one:** both discovery paths are on by default
(`read_config_from` has `agents_standard` and `claude`, both `true`), the source is
**silent** on which one wins when both exist, and `allowed-tools` defaults to *"all
tools"* — omitting is the **most permissive** option, not the most restrictive. What
carries the boundary is the `## Não faz` prose in the profile body, byte-identical in both
mirrors. Skills that are safe to dispatch declare `subagent: true` in `.agents/skills/`,
and each one states in its own text that it does not run destructive maintenance.

**`playbook` is the floor on all five platforms, not a rung that dispatch replaces.**
`sparkforge playbook <coordinator>` (CLI) or the `sparkforge_playbook` MCP tool returns the
same decomposition as a sequence of steps, reading the same `agents/` files a dispatching
coordinator would spawn as subagents: it loses the dispatch's parallelism, keeps the
method. It is the **only** path on Codex and Copilot CI — no source research measured
subagent support on either, and `parity.yaml` does not claim parity it has not measured.
And it stays the path on the three that do dispatch whenever dispatch is off: a user can
set `subagents_enabled: false`, and an org admin can pick *None* for "Default subagent
model", which disables subagents entirely. No file in this repository can prevent either.
Sources and verdicts: `knowledge/devin/agents-and-subagents.md`.

### How to actually invoke it

Everything above says **where** the profiles live and **what** the mirrors carry. This is
how you run them. Full walkthrough per platform, including the Devin Desktop caveat:
[`GUIA_DE_USO.md`](GUIA_DE_USO.md) (sections 2 and 3).

Dispatch, in plain language — there is no slash command for a profile on any of the three;
you name the profile and the task:

```text
Use the emr-infra-reviewer profile as a subagent to review this EMR cluster.
```

A dispatchable skill is invoked by name, and the harness decides whether it runs inline or
as a subagent (`subagent: true` says it is safe to dispatch; only two of the twelve also
name an `agent:`):

```text
Use the review-emr-cluster skill on this cluster dump.
```

The floor, which works on all five platforms and needs no dispatch at all:

```bash
sparkforge playbook emr-infra-reviewer --repo .   # or the sparkforge_playbook MCP tool
```

Start a Devin session by pointing it at the entry prompt, which is what
`scripts/install_skills.py` copies into a Devin target:

```text
Read PROMPT_INICIAL_MESTRE.md and use the glue-incremental-performance-architect skill.
```

## Deterministic evidence

Evidence for this project comes from deterministic extraction, not from an
LLM sampling the codebase. A `Fact` is an anchored observation — file, line,
symbol, snippet, or plan node — and it carries no judgment: no severity, no
threshold, no recommendation. A `Finding` is judgment, and it always carries a
non-empty `evidence` list of `fact_id` values plus a `rule_id` traceable to a
dated source in `rules/catalog/`. A `Finding` with empty evidence is invalid
by construction (see `sparkforge.findings.models.Finding.__post_init__`).

### What can be extracted

Sixteen extractors, all offline — they read artifacts already on disk and never
call AWS. Each has a CLI verb and an MCP tool with the same name, and together
they emit 102 distinct fact kinds:

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
| EMR on EC2 cluster | `analyze emr-cluster` | `describe-cluster` dump and the five that complete it |
| Data validation | `analyze data-quality` | the same `*.py`, read as checks rather than as work |
| Call graph | `analyze call-graph` | derived from PySpark facts |
| S3 object listing | `analyze s3-listing` | `s3api list-objects-v2` dump |
| Table consumers | `analyze consumers` | declared inventory, versioned in the repo |
| Terraform change | `analyze terraform-diff` | two states of the same module |
| Two runs compared | `benchmark` | two sets of event-log facts, before and after |
| Runtime | `runtime detect` | every source above, cross-checked |
| Correlation | `fuse` | facts from several extractors at once |

`analyze pyspark` and `analyze data-quality` read the same file and never
suppress each other: the same line can be `SF-PY-003` (what the chain costs)
and `SF-DQ-001` (the bad data was already published when the alarm rang) at
once. Neither area reads the other's fact namespace, and each judges
identically with and without the neighbour's facts — cross-suppression can only
be implemented by looking at the other's fact, so the invariant refuses both
the duplicate and the silence.

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
Glue 4.0 / 5.0 / 5.1 matrix and the Iceberg V3 versus Athena trap in Glue 5.1, and
`knowledge/emr/runtime-matrix.md` for the EMR 6.4.0 → 7.13.0 matrix and what the
`-amzn-N` suffix means. Outside Glue the release comes from the cluster dump, not from a
flag: `--emr` is a declaration, it loses to `describe-cluster` and to the event log, and
disagreeing with either becomes a reported divergence — never a silent substitution.

### Gates that actually block, and a report that carries proof

A case has four gates. They are **advisory by default** — the behaviour they have
always had. A case opened with `sparkforge case open --strict-gates` records that
choice **in the case file**, so it holds for the whole investigation: another
session, another machine, another tool inherits the rigour of whoever opened it.
Under it, `set_phase` refuses the transition while the evidence for the gates
guarding that phase is missing.

What unlocks a gate is evidence, never a flag: `case update --gate X --gate-value
true` still writes the boolean and still unlocks nothing. Which fact satisfies
which gate is **data** — the `gates` block of `rules/catalog/routing.yaml`, with
the exact command in `produced_by`. Only a gate **with** a producer can be
fail-closed: today `baseline_captured` (`bench.run_delta`) and `flows_mapped`
(`callgraph.reachable_spark_work`). The other two stay advisory, because
hardening a gate with no producer is the deadlock the Fase 0 design consciously
refused — a rigid gate is a dead end when the data simply does not exist.

When the data genuinely does not exist, overriding costs one sentence, and the
sentence stays: `case update --override-gate <gate> --reason "<why>"`, refused
without `--reason`, appended to a list (two overrides of the same gate are two
facts) and shown in `resume`. If the case has overrides, the report's "Gates com
override" section carries them — gate, date and reason — and it sits inside the
signed body, so deleting it after signing invalidates the signature.

Opening a case on top of an existing one is **refused**: overwriting would erase
the phase, the rigour and the recorded overrides. Starting over is still
possible, by name — `sparkforge case open --reopen` — and it **inherits** the
current `strict_gates`: rigour goes up with `--strict-gates` and never down by
forgetting a flag.

The gate checks **presence of the kind**, never the content of the fact. It
proves the analysis ran and produced the unlocking artifact — it does **not**
prove that it covered every `scope.entrypoints`, nor that the benchmark is of the
right job. Measured, so you do not overread a green gate: two hand-written lines
of JSON with empty `provenance` take a strict case from `intake` to `report`.
That limit is a recorded decision and it is stated in the blocking
message itself; state the same caveat in the report, the way `dq.unresolved`
states its own.

`sparkforge report sign --report <md> --findings <json>` appends a signature
block to the report, and `sparkforge report verify` says **which** of the four
parts diverged — signature version, evidence, catalog, or body — rather than just
"invalid". `version_mismatch` means the rule changed, not that the body was
tampered with: the body comes back as **not assessable** instead of accused. Both
exist as MCP tools too (`sparkforge_report_sign`, `sparkforge_report_verify`).
The input is the **findings** file, not the facts file: `rule_id`,
`catalog_version` and `schema_version` only exist there. The hash covers the
cited `fact_id`s, the `rule_id`s that fired, both versions, and the report
**body** — without the body, the whole text could be rewritten while the
signature still verified.

It proves **correspondence**, never **authorship**: there is no key and no
secret, and anyone holding the same findings produces the same signature. Do not
let a reader take the block for authentication — the limit is written inside the
block the report carries. Text appended after the block is rejected, not ignored;
editing the prose after signing invalidates, which is the point, and re-signing
is cheap.

The `recommendation:` schema documented above remains valid: `Finding` is a
compatible superset of it, with the same fields (`title`, `severity`,
`evidence`, `proposed_change`/`expected_effect`, `risks`, `tradeoffs`,
`validation`, `rollback`) plus the anchoring (`subject`, `rule_id`,
`sources`) that makes each field traceable rather than asserted.

See `AGENT_PROTOCOL.md` for the operating rules every skill and agent are
injected with, and `docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md`
for the full Fact/Finding contract.
