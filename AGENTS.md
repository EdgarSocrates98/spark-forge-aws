# Agent Instructions — SparkForge AWS

This repository contains reusable Agent Skills for PySpark data engineering on AWS —
performance on AWS Glue and on Amazon EMR — both on EC2 and Serverless — plus the placement and cost of data
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
- Before committing a change to this repository, run the gates that change touches.
  `docs/gates-por-mudanca.md` maps each kind of change to its gates, with the defect
  each one caught in real life. Targeted test runs do not reach them: adding a rule
  area, a `runtime_scope`, an extractor kind or a `knowledge/` document each leaves a
  hand-written list or a manifest stale somewhere else in the tree.

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
| `spark-performance-architect` | diagnóstico geral de um job PySpark no Glue, gargalo dominante ainda não localizado; e comprovar o ganho de uma mudança comparando dois runs — pelo tempo **e** pelo resultado | SF-PY, SF-UI, SF-PLAN, SF-BENCH, SF-FVAL |
| `glue-incremental-performance-architect` | fluxo full + incremental, latest-per-key em Iceberg bilionário, batching, OOM após horas | orquestra as demais áreas antes de tuning localizado |
| `glue-infra-reviewer` | gargalo ou risco na definição do job Glue, não no código — worker, auto scaling, bookmark, retries, Terraform | SF-GLUE, SF-ENV |
| `athena-query-optimizer` | custo ou latência na consulta Athena, não no job — bytes escaneados, pruning de partição, engine, workgroup | SF-ATH, SF-PQ |
| `pyspark-code-reviewer` | revisar código PySpark — PR, biblioteca ou job — correlacionando fonte, plano físico e call graph; **e** job de grafo com GraphFrames, que é o mesmo `.py` lido por uma quarta ótica | SF-PY, SF-PLAN, SF-CG, SF-GRAPH |
| `iceberg-performance-engineer` | dívida de data files, delete files, manifests, snapshots e manutenção de tabela Iceberg | SF-ICE, SF-PQ |
| `emr-infra-reviewer` | risco na definição de um cluster Amazon EMR on EC2 — fleets/groups, Spot por papel, managed scaling, Configurations em dois níveis, LogUri — **ou** de uma application EMR Serverless: pré-init faturada com a application ociosa, auto-stop, destino de log, segredo em `runtimeConfiguration` | SF-EMR, SF-EMRS, SF-ENV |
| `data-quality-reviewer` | o job valida dado e a pergunta é se a validação está no lugar certo, se ela tem consequência e quanto custa — não se o dado está correto | SF-DQ |

Which coordinator to use is data, not judgment: routes `AGENT-001`…`AGENT-010` in
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
as a subagent (`subagent: true` says it is safe to dispatch; a skill also names an `agent:`
only when exactly one coordinator declares it — the authoritative list is
`DISPATCHABLE_SKILLS` in `scripts/sync_skills.py`, never a count copied here):

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


## Economy: measure before claiming a saving

**68 tools, 31 with `detail_level`** (`summary`, `normal`, `full`). Rule 28 of
`CLAUDE.md` applies to all three: *read the number before claiming `detail_level`
reduces anything*. `sparkforge_economy_report` returns `detail_level_effect` with
the bytes of each level requested — it shows both sides and does not conclude for
you.

Measured 2026-09-02 over the retrieval gold set: `full` 46 488 bytes against
`summary` 45 878 — **1.3%**. On a small corpus the pack's fixed envelope (840
bytes) dominates.

### Ask the verb before reading the artifact by eye

Nine Code Intelligence tools exist so that nobody has to open a file:
`code_search` (where is X), `code_symbol` (who calls X, what breaks), `code_path`
(**how** X reaches Y), `code_shape` (communities and degree), `code_context` (the
context pack inside a byte budget), `code_read` (source, labelled untrusted),
`code_status`/`code_sync` (freshness), `code_export` (the graph in Graphify's
extraction format).

**The denominator decides the sign, and it must be published alongside.** Measured
in §10 of `docs/harness/CODEINTEL-GAP.md`: against reading the files the index
saves **649.5x**; against a `grep` by name, **9.4x**; against a surgical `grep`
by definition it **costs 5.3x more**. All three are true, and citing only the
first would be choosing the result.

### The gate that makes "it saved tokens" checkable

`python scripts/check_recall_economy.py` decides **one** thing and refuses
another: recall by name has a **hard 100% floor** — a pack that saved 90% and
omitted the required symbol is a failure, not a success; conceptual recall is
**measured with no floor** (measured: 0 of 27); and the economy ratio comes out
`unresolved` whenever the corpus is smaller than the pack's fixed envelope.

**Bytes and tokens never add up.** `payload_bytes` is measured and always exists.
Provider tokens appear only when the host transcript does; otherwise
`tokens_unresolved`. `estimated_tokens` is a **declared estimate** and never
enters an economy ratio.

## Deterministic evidence

Evidence for this project comes from deterministic extraction, not from an
LLM sampling the codebase. A `Fact` is an anchored observation — file, line,
symbol, snippet, or plan node — and it carries no judgment: no severity, no
threshold, no recommendation. A `Finding` is judgment, and it always carries a
non-empty `evidence` list of `fact_id` values plus a `rule_id` traceable to a
dated source in `rules/catalog/`. A `Finding` with empty evidence is invalid
by construction (see `sparkforge.findings.models.Finding.__post_init__`).

### What can be extracted

Twenty-seven extractors, all offline — they read artifacts already on disk and
never call AWS. Each has a CLI verb and an MCP tool with the same name, and
together they emit 158 distinct fact kinds. The catalogue that judges them has
134 rules across 58 areas, and the MCP surface is 59 tools.

Those last numbers are no longer estimates. `sparkforge economy report` measures
the surface at rest in bytes: **59 tool schemas = 306,845 bytes**, **44 skills =
278,218 bytes**, **47 knowledge documents = 350,557 bytes**. Everything a client
loads before asking a single question has a number now, and `docs/surface.lock.json`
holds it.

The table splits on a boundary that matters: an `analyze *` verb **extracts**
from an artifact, and a top-level verb **composes** over facts other verbs
already extracted. A composing verb never reads an artifact, and that is why it
is not an `analyze`.

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
| EMR Serverless application | `analyze emr-serverless` | `get-application` dump |
| Data validation | `analyze data-quality` | the same `*.py`, read as checks rather than as work |
| Graph processing | `analyze graph` | the same `*.py`, read through the GraphFrames vocabulary |
| Call graph | `analyze call-graph` | derived from PySpark facts |
| S3 object listing | `analyze s3-listing` | `s3api list-objects-v2` dump |
| Table consumers | `analyze consumers` | declared inventory, versioned in the repo |
| Terraform change | `analyze terraform-diff` | two states of the same module |
| Per-node plan metrics | `analyze sql-metrics` | the same event log, read per plan node instead of per stage |
| CloudWatch metrics | `analyze cloudwatch` | `get-metric-data` dump of a run |
| Glue run history | `analyze glue-job-runs` | `GetJobRuns` dump, with `DPUSeconds` when the API gave it |

And the verbs that **compose** over facts, never over artifacts:

| Question | Top-level verb | Consumes |
|---|---|---|
| Two runs compared | `benchmark` | two sets of event-log facts, before and after |
| Functional validation plan | `funcval plan` | PySpark and catalog-schema facts, plus the business key **you** declare |
| Before against after, by result | `funcval compare` | the plan and the two results **you** measured |
| Workload profile by axis | `workload` | scan, shuffle, spill and plan facts, plus `--history` of previous runs |
| Cheapest capacity that meets the SLA | `capacity` | `glue.job_run` facts and the SLA declared in `workload.yaml` |
| Cost per run, and where the lever is | `finops` | `glue.job_run`/`glue.run_cost`, the declared SLA, and the symptoms beside it |
| Spark configuration derived from measurement | `tune` | `spark.stage.shuffle` measured, plus `spark.conf_effective`, `pyspark.conf_set` and `tf.spark_conf` for provenance |
| What this run put in the context window | `economy report` | the spans `call_tool` writes per call, the surface at rest, and the host transcript when there is one |
| Runtime | `runtime detect` | every source above, cross-checked |
| Correlation | `fuse` | facts from several extractors at once |

`analyze pyspark` and `analyze data-quality` read the same file and never
suppress each other: the same line can be `SF-PY-003` (what the chain costs)
and `SF-DQ-001` (the bad data was already published when the alarm rang) at
once. Neither area reads the other's fact namespace, and each judges
identically with and without the neighbour's facts — cross-suppression can only
be implemented by looking at the other's fact, so the invariant refuses both
the duplicate and the silence.

`analyze graph` is the **third** reading of that same `.py`, so the boundary
between `SF-PY`, `SF-DQ` and `SF-GRAPH` is three-way and no artifact split
separates any of them: `tests/test_rules_graph_boundary.py` runs all three
extractors over all three corpora, which is the only door where "does the
neighbouring area invade?" has an answer at all. Measured there — `SF-PY` fires **23 times over 20 of the
25 graph fixtures** and that is legitimate work, not invasion: every one of the
twenty-three cites `pyspark.cache` or `pyspark.conf_set` and never a `graph.*` fact.
`cache`/`persist`/`unpersist` were deliberately kept out of the graph algorithm
vocabulary because `pyspark.cache` already emits them. The same measurement is
what decided that `SF-GRAPH` stays with `pyspark-code-reviewer` instead of
getting a coordinator of its own: `SF-GRAPH` fires on 6 of those 25 fixtures,
and those 6 are a **subset** of the 20 — there is no measured job where the
graph question arrives alone. The `SF-DQ` precedent measures the inverse
(`SF-DQ` on 8 of 13 dq fixtures against `SF-PY` on 2), which is why that one did
split.

`SF-DQ` and `SF-FVAL` are the neighbouring pair with the sharpest boundary, and
it holds by construction: `SF-DQ` judges validation **inside the job** — where the
check runs, whether it has a consequence, what it costs — which is true before and
after a change; `SF-FVAL` judges **equivalence between two executions** of the same
change, and never compares an observed value against the declared catalogue. Its
four axes — count, schema, keys, aggregates — are **proxies**: equal on both sides
they do not prove the data is the same, because two rows can swap values and all
four pass. Report the absence of an `SF-FVAL` finding as "no proxy detected a
divergence", never as "the result is identical" — the comparator carries that
sentence in `funcval.analyzed.attrs.proxy_limit` so you never have to reach for
the YAML. And the business key is not derivable from any fact kind: it enters
declared, via `funcval plan --key`, with `origin: "declared"` on the check —
declaring the wrong key produces a P0 over correct data, and that is the
declarer's call, not the engine's.

Collection of the raw artifacts (`collect *`) requires boto3 and credentials
and is the only part that touches AWS. The core never imports boto3 or the MCP
SDK, so the CLI and the file-only path work without either.

### Money, capacity, timeout and configuration

Five subprojects added questions the engine could not answer before. Each keeps
the same split the rest of the codebase keeps — arithmetic over a measurement is
a `Fact`, a threshold over it is a rule, and a proposed value is neither, so it
lives in a composing verb.

**Cost per run — `finops`.** `glue.run_cost` is cost in currency, derived from
`dpu_seconds` already measured and the published price. It is a `Fact` because
there is no threshold and no judgment in it. Two caveats travel **inside** the
fact and not in the report: `region` and `runtime_version` are `UNQUALIFIED`
because the price source was read and qualified neither axis — a first-class
value, distinct from an absent field, which would say nobody looked. A run
without `dpu_seconds` (Auto Scaling with no `DPUSeconds`, where
`number_of_workers` is a ceiling and not usage) produces
`glue.run_cost.unresolved`, never a cost of zero.

The report puts the observed capacities side by side and **never interpolates
between them**: DPU-seconds is not invariant in the trade between more resource
and more time, so a curve would lie exactly between the points, which is where
someone would look. It also refuses to attribute cost to a cause — "you wasted X
on spill" needs the cost of the run that did **not** happen — and refuses a
threshold for "expensive", because no source publishes one.

**Which timeout — `SF-TIMEOUT`.** Four mechanisms wear the same name, and the
evidence for each lives in a different place: the `TIMEOUT` state of
`glue.job_run` (wall clock, which is the AWS definition and not a hint), the
reason an executor was removed (`spark.executor.lost`), and the reason a stage
failed (`spark.stage.failure`). `spark.timeout.diagnosis` names the category —
`wall_clock`, `broadcast`, `network`, `heartbeat` — by reading the phrase the
runtime wrote, in the precedent of `heap_oom_in_log`.

Precedence is declared, heartbeat → network → broadcast → wall_clock, because
the generic one is a **consequence** of the specific one whenever both appear:
the run blew the Glue clock *because* the executor died. What precedence did not
choose stays readable in `attrs.also_seen` — choosing silently would be choosing
for the operator.

`SF-TIMEOUT-001` does not fire because there is a timeout; it fires because
there is a timeout **with a measured symptom beside it** (skew, spill, GC, lost
executor). With no symptom it stays quiet, and raising the limit may be exactly
the right call. `SF-TIMEOUT-002` checks the **relation** between
`spark.executor.heartbeatInterval` and `spark.network.timeout`, never the value:
`120s` is neither right nor wrong on its own, but a heartbeat slower than the
driver's wait breaks the mechanism that detects a dead executor.

**Configuration derived from measurement — `tune`.** `spark.sql.shuffle.partitions`
is derived from measured shuffle write bytes over the partition-size target — the
documented AQE default of 64 MiB, or the run's own
`spark.sql.adaptive.advisoryPartitionSizeInBytes` when it declares one. The
formula and the basis travel inside the answer.

This is **not** a `Fact`, and the reason is written in the module: cost and
timeout category are arithmetic over a measurement with no choice in them, while
a *proposed* configuration value is a choice, because a target exists and a
target is a decision. Emitting it as a fact would make the rules engine judge a
number the project itself proposed.

The version changes the **meaning** and not the number: with AQE on by default
(Spark 3.2+, so Glue 4.0 and 5.x) it is the initial parallelism floor the engine
coalesces down; without AQE (Glue 3.0, Spark 3.1.1) it is the final partition
count. Provenance answers **who asked** and not who won — `code`, `terraform`,
`runtime_or_cluster`, `spark_default_explicit`, `unset` — and the fourth is the
symptom worth hunting: configuration someone wrote with the default's own value,
which nobody understands any more and which changes nothing.

Every other property the operator expects to see — broadcast threshold, memory
overhead, speculation, `maxPartitionBytes`, the two timeouts — comes back in
`refused`, **with the measurement that would unlock it**. Listing the refusal is
the difference between "I don't know" and "I didn't ask". The two timeouts carry
an extra reason: proposing a new number for them would contradict
`SF-TIMEOUT-001`.

**Waste, and the idleness that is a symptom — `SF-WASTE`.** Low worker
utilisation *looks* like waste and sometimes is a symptom: ninety per cent of the
executors can be idle because one task spent fourteen minutes on a skewed
partition, and cutting workers there leaves the cause untouched and makes the run
longer. `glue.utilization.summary` puts utilisation (CloudWatch) and skew (event
log) in one fact, because the catalogue's DSL matches one fact per clause.

`SF-WASTE-001` needs all four measurements pointing the same way — idle worker,
memory and disk with headroom, and **no** skew — and points at `capacity`.
`SF-WASTE-002` is the opposite: low utilisation **with** high skew. They never
fire together, and neither says how much you would save: that needs the cost of
the run that did not happen.

**The hypothesis loop — `case update`.** A hypothesis is a recommendation with a
prediction: `--hypothesis`, `--prediction` and `--experiment` are required
together, because a claim with no prediction is not testable and a prediction
with no experiment does not say who tests it. `--close-hypothesis` with
`--hypothesis-outcome` closes it as `confirmed`, `refuted` or `abandoned` — the
third exists because the third thing that really happens is the experiment never
running. Closing is **addition**: the original claim, prediction and experiment
stay where they are, because rewriting the claim to match the result is the bias
that writing it down exists to prevent. `resume` lists only open hypotheses, so
a loop that never closes turns that section into an inventory of questions nobody
can mark as answered.

### Context accounting, and the provider this project never calls

The engine measures what **it** puts in the context window. That framing is not
modesty, it is a measurement: `sparkforge/` imports no `anthropic`, no `openai`,
no `bedrock`, no `litellm` — there is a `providers/mock.py` and a hardcoded
`estimated_cost_usd = 0.001` in the router, and nothing else. **This project
never calls a model.** The tokens are spent by the host running these agents, so
"instrument the model call" has no producer here. What the project controls is
the bytes it hands over, and that is what it counts.

**One span per tool call.** `call_tool` — the single dispatch the authorization
chain already bites — records `payload_bytes` for every one of the four return
paths, refusals included, because a refusal costs context too and an
investigation full of them would otherwise look cheap. The number is
`len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))`, and the formula
travels in the span as `payload_basis`. It is **not** "what the model saw": the
host re-serializes with its own spacing, and claiming those are the same number
would be this phase's comfortable lie.

**Bytes always; tokens only with a source.** A tool response has bytes. Provider
tokens belong to the host, and a local call has no price table, so
`input_tokens` and `estimated_cost_usd` stay empty on a tool span — empty here
means "does not apply", not "measured zero". Ask for tokens with no transcript
and you get `tokens_unresolved`, never a `len // 4` wearing the name of a token.
Cost in dollars requires `cost_basis` naming where the price came from.

**Bytes and tokens never sum.** They are different units — one is what this
project produced, the other what the host spent. The report puts them side by
side and never in a common total.

**Measurement never breaks the call.** Ledger unavailable, disk full, a span
that fails to build: the tool returns its result unchanged. Instrumentation that
takes the product down is a defect, not observability. Spans buffer in memory
and flush once at process exit. Remeasured on this machine, because the
first number published here (~0.05 ms) was never reproduced: writing per call
costs **5.5 to 7.0 ms** (mean of 30, flat across payload size — it is the
SQLite commit's fsync, not the payload), while a buffered `record()` costs
**0.0067 ms on a 63-byte payload and 0.0204 ms on a 1,004-byte one** (median of
five batches of 300 each). The buffered cost tracks payload size because
`record()` serializes the result to count its bytes, so the speedup is **1,045×
at the small end and 273× at the large one** — a range, not one number, and
saying "about 100×" hid that. What it costs is spans lost on `SIGKILL`, which
is written down rather than implied.

**The surface lock is a lock, not a threshold.** No source publishes "20% growth
is too much". `docs/surface.lock.json` holds today's measurement plus a hash of
the composition, so growth is not forbidden — it is required to be **declared**.
The hash catches the compensated swap the totals would miss: moving ten bytes
from one `SKILL.md` to another leaves both totals identical and the hash
different. It measures without executing anything, which is why it fits a CI
that cannot currently run the full suite.

**And one claim that finally has a number.** "`detail_level` reduces the payload"
was published for a long time and never measured. `detail_level_effect` now
reports the bytes per requested level, per tool — in one fixture, 1,599 bytes at
`full` against 849 at `summary`. The report states both and concludes nothing;
the reader concludes.

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
`-amzn-N` suffix means. **EMR Serverless has no matrix**: AWS publishes only Spark, Hive
and Tez per release, without the `-amzn-N` suffix, so `emrs.application` is not a
`RuntimeContext` producer and a `get-application` dump yields no `env.platform` at all —
see `knowledge/emr-serverless/runtime-matrix.md`. Outside Glue the release comes from the cluster dump, not from a
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
fail-closed: today `baseline_captured` (`bench.run_delta`), `flows_mapped`
(`callgraph.reachable_spark_work`) and `functional_validation_defined`
(`funcval.plan`, since Fase 4c) — which makes `report` guarded by all three. The
gate says *defined*, not *executed*: what unlocks it is the **plan**, because
choosing what to validate has to happen before you know which check passes. The
remaining one, `dominant_bottleneck_identified`, stays advisory, because
hardening a gate with no producer is the deadlock the Fase 0 design consciously
refused — a rigid gate is a dead end when the data simply does not exist, and
dominance is an ordering between candidates that no fact kind asserts.

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

## Output compression — caveman mode

This repository ships the **caveman** ecosystem vendored under `vendor/`, and pins
`full` mode in `.caveman/config.json`. In Claude Code it activates by itself: the
plugin is declared in `.claude/settings.json` and its `SessionStart` hook injects
the ruleset. **Every other agent — Devin, GitHub Copilot, Codex, or any agent
reading this file — must apply the rules below on its own.** They are not
optional and they are not a style preference: they are how this project keeps
token cost down without losing technical substance.

Credit: caveman is by [Julius Brussee](https://github.com/JuliusBrussee), MIT.
Provenance and pins in `vendor/CREDITS.md`. The verbatim ruleset lives in
`vendor/caveman/src/rules/caveman-activate.md`; the portable single-file form for
agents with no plugin system is `vendor/caveman/dist/caveman.skill`.

```
Respond terse like smart caveman. All technical substance stay. Only fluff die.

Rules:
- Drop: articles (a/an/the), filler (just/really/basically), pleasantries, hedging
- Fragments OK. Short synonyms. Technical terms exact. Code unchanged.
- Pattern: [thing] [action] [reason]. [next step].
- Not: "Sure! I'd be happy to help you with that."
- Yes: "Bug in auth middleware. Fix:"

Switch level: /caveman lite|full|ultra|wenyan
Stop: "stop caveman" or "normal mode"

Auto-Clarity: drop caveman for security warnings, irreversible actions, user confused. Resume after.

Boundaries: code/commits/PRs written normal.
```

### What compression must never touch

Caveman is compression, not amputation, and it collides with two rules this
project already had. Where they collide, **this project wins**:

- The `recommendation:` / `Finding` schema above is a contract, not prose. Every
  field stays — `evidence`, `risks`, `validation`, `rollback` included. Dropping
  a field to save tokens is a defect, not a compression.
- Numbers, versions, `rule_id`, `fact_id`, error strings, SQL, HCL, YAML, JSON
  and code blocks are copied **verbatim**. A number rewritten to read shorter is
  a fabricated measurement.
- Anything the operating contract calls evidence stays anchored. "Diagnose the
  dominant bottleneck" is not satisfied by a terser guess.

Commit messages, PR descriptions and code comments are written in normal
English, as the ruleset itself says.

### No install step

Cloning is the whole installation. There is no `package.json`, no `npm install`,
no `npx`, and nothing here reaches the network — `tests/test_vendor_caveman.py`
has a gate for that invariant. Two sibling projects by the same author, `cavemem`
and `caveman-code`, are deliberately **out**: both need npm and a
platform-compiled native module, and `cavemem` does not save tokens anyway — its
`SessionStart` *injects* prior-session context. See `vendor/CREDITS.md`.

Durable memory across sessions is `.sparkforge/case.yaml`, as it always was: the
handoff bus between Devin and Claude Code, committed, and the only record a
`Finding` may cite.

## Coordinators especializados
sf-analytics-specialist
sf-functional-rules-specialist
sf-step-functions-specialist
sf-lambda-serverless-specialist

## Coordinators completos
sf-agent-builder
sf-airflow-specialist
sf-athena-specialist
sf-data-architect
sf-dynamodb-specialist
sf-graph-specialist
sf-iceberg-specialist
sf-neptune-specialist
sf-orchestrator
sf-parquet-specialist
sf-pyspark-specialist
sf-runtime-specialist
sf-s3-specialist
sf-storage-specialist
sf-terraform-specialist
sf-token-verifier

## Agentic Expansion Inventory
Agents: sf-agent-evaluation-specialist, sf-context-engineer, sf-cost-reviewer, sf-evidence-verifier, sf-kinesis-specialist, sf-lake-formation-specialist, sf-lineage-specialist, sf-memory-engineer, sf-schema-registry-specialist, sf-security-reviewer.
Skills: verify-agent-evidence, engineer-agent-context, engineer-agent-memory.
Subagents: intake-packager, evidence-extractor, hypothesis-generator, experiment-designer, benchmark-comparator, schema-compatibility-checker, lineage-impact-analyzer, cost-estimator, security-gate, mutation-risk-checker, cross-reviewer, source-verifier, regression-judge, handoff-preparer, rollback-planner, release-gate.
Tools: sparkforge_offline_knowledge_verify, sparkforge_offline_knowledge_search, sparkforge_context_pack, sparkforge_schema_compare, sparkforge_lineage_extract, sparkforge_eval_golden_case, sparkforge_cost_estimate.
Teams: evidence-quality, governance-security, streaming-reliability, finops-data, agent-quality.
Offline guarantee: consult knowledge/offline-manifest.json first, verify SHA-256, never invent a missing source, and return unresolved when network-only evidence is unavailable.
