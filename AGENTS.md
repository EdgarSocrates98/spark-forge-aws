# Agent Instructions — SparkForge AWS

This repository contains reusable Agent Skills for PySpark data engineering on AWS —
performance on AWS Glue and on Amazon EMR — both on EC2 and Serverless — plus the placement and cost of data
validation inside the job.

This file is loaded on every session, so it keeps **rules and pointers**, not history.
Dated narrative that used to live here is in `docs/historico/instrucoes-arquivadas.md`,
and `tests/test_bootstrap_budget.py` caps its size. Live figures live in the *Números
correntes* table of `docs/superpowers/STATUS.md`, checked by
`scripts/check_status_numbers.py --strict`.

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
  each one caught in real life.

## Developing this repository: the in-repo SDD

Non-trivial changes go through the skills `sdd-explore`, `sdd-define`, `sdd-design`,
`sdd-plan`, `sdd-build` and `sdd-ship`. Artifacts live in `docs/sdd/<FEATURE>/`, and
each phase is checked by `sparkforge sdd check --repo . --feature <F>` (plus
`sdd status` and `sdd stamp`). Here they replace the spec/plan/TDD cycle of other
plugins (superpowers, AgentSpec); `docs/superpowers/specs/` and `plans/` are frozen,
and the AgentSpec history is archived in `docs/sdd/archive/agentspec/`. Flow:
`docs/sdd/README.md`.

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
(`sf-inventory`, `sf-extractor`, `sf-judge`, `sf-verifier`, `sf-synthesizer`, in
`agents/executors/*.md`, each with an explicit `## Não faz` boundary and a
`## Pressupõe`/`## Entrega` handoff contract). A coordinator does not execute: it reads
the case, decides which executor runs next, and records which one ran
(`sparkforge_case_update` with `skills_used`; see `AGENT_PROTOCOL.md` rule 6).

| Coordinator | Use quando… | `rule_areas` |
|---|---|---|
| `spark-performance-architect` | diagnóstico geral de um job PySpark no Glue, gargalo dominante ainda não localizado; e comprovar o ganho de uma mudança comparando dois runs — pelo tempo **e** pelo resultado | SF-PY, SF-UI, SF-PLAN, SF-BENCH, SF-FVAL |
| `glue-incremental-performance-architect` | fluxo full + incremental, latest-per-key em Iceberg bilionário, batching, OOM após horas | orquestra as demais áreas antes de tuning localizado |
| `glue-infra-reviewer` | gargalo ou risco na definição do job Glue, não no código — worker, auto scaling, bookmark, retries, Terraform | SF-GLUE, SF-ENV |
| `athena-query-optimizer` | custo ou latência na consulta Athena, não no job — bytes escaneados, pruning de partição, engine, workgroup | SF-ATH, SF-PQ |
| `pyspark-code-reviewer` | revisar código PySpark — PR, biblioteca ou job — correlacionando fonte, plano físico e call graph; **e** job de grafo com GraphFrames | SF-PY, SF-PLAN, SF-CG, SF-GRAPH |
| `iceberg-performance-engineer` | dívida de data files, delete files, manifests, snapshots e manutenção de tabela Iceberg | SF-ICE, SF-PQ |
| `emr-infra-reviewer` | risco na definição de um cluster Amazon EMR on EC2 **ou** de uma application EMR Serverless | SF-EMR, SF-EMRS, SF-ENV |
| `data-quality-reviewer` | o job valida dado e a pergunta é se a validação está no lugar certo, se tem consequência e quanto custa | SF-DQ |

Which coordinator to use is data, not judgment: routes in `rules/catalog/routing.yaml`
map the case's phase and dominant finding area to a `recommended_agent`, and
`sparkforge_next_step` / `sparkforge next-step` reads them — never pick a coordinator by
inspection.

**Three platforms dispatch**: Claude Code, the Devin CLI and the Devin Local agent. Devin
reads `.agents/agents/` natively and imports `.claude/agents/*.md` — both are generated
mirrors of `agents/`, so the eight coordinators are subagent profiles there. The five
executors are not at a documented discovery layout (`executors/` is neither flat nor
`agents/<name>/AGENT.md`), so do not presume they are published. A coordinator dispatched
as a subagent does **not** dispatch the executors: subagents cannot spawn subagents, so
the decomposition runs inline. The `.agents/` mirror drops `tools:` (the value mapping is
undocumented) and never gains `model:`; **dropping `tools:` is not a security boundary** —
omitting is the most permissive option. What carries the boundary is the `## Não faz`
prose, byte-identical in both mirrors. Sources: `knowledge/devin/agents-and-subagents.md`.

**`playbook` is the floor on all five platforms.** `sparkforge playbook <coordinator>`
(or `sparkforge_playbook`) returns the same decomposition as a sequence of steps. It is
the **only** path on Codex and Copilot CI, and stays the path on the three that dispatch
whenever dispatch is off (`subagents_enabled: false`, or an org admin picking *None*).

### How to actually invoke it

Full walkthrough per platform: [`GUIA_DE_USO.md`](GUIA_DE_USO.md) (sections 2 and 3).
There is no slash command for a profile; name the profile and the task:

```text
Use the emr-infra-reviewer profile as a subagent to review this EMR cluster.
Use the review-emr-cluster skill on this cluster dump.
```

The authoritative list of dispatchable skills is `DISPATCHABLE_SKILLS` in
`scripts/sync_skills.py`. The floor, needing no dispatch:

```bash
sparkforge playbook emr-infra-reviewer --repo .   # or the sparkforge_playbook MCP tool
```

Start a Devin session with: `Read PROMPT_INICIAL_MESTRE.md and use the
glue-incremental-performance-architect skill.`

## Economy: measure before claiming a saving

**106 tools, 38 with `detail_level`** (recounted 2026-09-16) (`summary`, `normal`, `full`).
Rule 28 of `CLAUDE.md` applies: *read the number before claiming `detail_level` reduces
anything*. `sparkforge_economy_report` returns `detail_level_effect` with the bytes of
each level requested and does not conclude for you.

Nine Code Intelligence tools exist so that nobody has to open a file: `code_search`,
`code_symbol`, `code_path`, `code_shape`, `code_context`, `code_read`,
`code_status`/`code_sync`, `code_export`. **The denominator decides the sign**: against
reading files the index saves a lot, against a `grep` by name much less, against a
surgical `grep` by definition it costs more — dated figures in §10 of
`docs/harness/CODEINTEL-GAP.md`. `python scripts/check_recall_economy.py` enforces a hard
100% floor on recall by name and returns the ratio `unresolved` when the corpus is
smaller than the pack's fixed envelope. **Bytes and tokens never add up**
(`CLAUDE.md` rules 22 and 24).

## Deterministic evidence

Evidence comes from deterministic extraction, not from an LLM sampling the codebase. A
`Fact` is an anchored observation — file, line, symbol, snippet, or plan node — and
carries no judgment. A `Finding` is judgment: it always carries a non-empty `evidence`
list of `fact_id` values plus a `rule_id` traceable to a dated source in
`rules/catalog/`. A `Finding` with empty evidence is invalid by construction
(`sparkforge.findings.models.Finding.__post_init__`). Extractors are offline — they read
artifacts already on disk and never call AWS; only `collect *` touches AWS, and the core
never imports boto3 or the MCP SDK.

Every executable rule carries an `action:` block (`kind`, `target`, `direction`,
`requires_absent`, `moves`, `depends_on`) in a closed vocabulary locked in both
directions by a gate — see any rule in `rules/catalog/`, e.g. `SF-WASTE-001` in
`rules/catalog/waste.yaml`. `expected_gain` is **refused by schema**: asserting how much
you would save requires the cost of the run that did not happen (`CLAUDE.md` rule 13).

An `analyze *` verb **extracts** from an artifact; a top-level verb **composes** over
facts other verbs already extracted and never reads an artifact:

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
| Per-node plan metrics | `analyze sql-metrics` | the same event log, read per plan node |
| CloudWatch metrics | `analyze cloudwatch` | `get-metric-data` dump of a run |
| Glue run history | `analyze glue-job-runs` | `GetJobRuns` dump, with `DPUSeconds` when the API gave it |

The composing verbs and the question each answers are the table at the top of
`CLAUDE.md` (`workload`, `capacity`, `finops`, `tune`, `economy report`, `benchmark`,
`funcval`, `arbitrate`, `change`, `report github`, `telemetry export`, `resume`).

`SF-PY`, `SF-DQ` and `SF-GRAPH` read the same `.py` and never suppress each other; each
judges identically with and without the neighbour's facts. `SF-FVAL`'s four axes (count,
schema, keys, aggregates) are **proxies**: report the absence of an `SF-FVAL` finding as
"no proxy detected a divergence", never as "the result is identical". The business key
enters **declared** (`funcval plan --key`), never derived.

### Money, capacity, timeout and configuration

Arithmetic over a measurement is a `Fact`, a threshold over it is a rule, and a proposed
value is neither, so it lives in a composing verb (`CLAUDE.md` rule 11). The rules that
govern `finops`, `capacity`, `SF-TIMEOUT`, `tune` and `SF-WASTE` are `CLAUDE.md` rules 11
to 21: no interpolation between observed capacities, no cost attributed to a cause, no
cost without `dpu_seconds`, "timeout" is four categories, a relation between two
properties is checkable while an isolated value is not, low utilisation with high skew is
a symptom, the version changes the meaning of the number, provenance says who **asked**,
every property without its measurement comes back in `refused` with the measurement that
would unlock it, and a hypothesis has three parts and one outcome (closing is addition).

### Context accounting

`sparkforge/` imports no `anthropic`, no `openai`, no `bedrock`, no `litellm`: **this
project never calls a model** (`CLAUDE.md` rule 23). `call_tool` records `payload_bytes`
for every call, refusals included; provider tokens appear only with a host transcript,
otherwise `tokens_unresolved`; cost in dollars requires `cost_basis`; measurement never
breaks the call; the surface lock requires growth to be **declared** (`CLAUDE.md` rules
22 to 27).

### Three states, never two

**Absence of evidence is not evidence of absence.** When an artifact does not answer a
question, the extractor emits an `*.unresolved` fact naming the blind spot, and the rule
that depended on it does not fire. Report the blind spot; never fill it in.

### Version guard

Every rule declares `runtime_scope`, and the engine skips it when the detected runtime is
out of range — so state the detected runtime before any finding. Divergence between
sources is never resolved by picking one: it is `SF-ENV-001` at P0. Matrices:
`knowledge/glue/runtime-matrix.md`, `knowledge/emr/runtime-matrix.md`; **EMR Serverless
has no matrix** (`knowledge/emr-serverless/runtime-matrix.md`). Outside Glue the release
comes from the cluster dump; `--emr` is a declaration that loses to `describe-cluster` and
to the event log, and disagreement becomes a reported divergence.

### Gates that actually block, and a report that carries proof

A case has four gates, advisory by default. `sparkforge case open --strict-gates` records
rigour **in the case file**, and `set_phase` then refuses a transition while the evidence
for its gates is missing. What unlocks a gate is evidence (the fact kind named in the
`gates` block of `rules/catalog/routing.yaml`), never `--gate-value true`. When the data
genuinely does not exist, `case update --override-gate <gate> --reason "<why>"` records
who passed over what and why. The gate checks **presence of the kind**, never the content
of the fact — state that caveat in the report.

`sparkforge report sign` appends a signature block and `sparkforge report verify` says
**which** part diverged (signature version, evidence, catalog, or body). It proves
**correspondence**, never **authorship**: there is no key. The `recommendation:` schema
above remains valid: `Finding` is a compatible superset of it.

See `AGENT_PROTOCOL.md` for the operating rules every skill and agent are injected with,
and `docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md` for the full
Fact/Finding contract.

## Access governance: the four artifacts that answer "who may do what"

```bash
sparkforge analyze terraform --path infra/ --out .sparkforge/facts_tf.json
sparkforge collect lakeformation --repo . --database <db> --table <t>     --catalog-id <catalog-owning-account> --resource-arn <s3-location> --now <ISO8601>
sparkforge analyze lakeformation-grants --path .sparkforge/artifacts/lakeformation/
sparkforge collect iam-access --repo . --role-arn <runtime-role>     --resource-arn <target-arn> --action s3:PutObject --now <ISO8601>
sparkforge analyze iam-access --path .sparkforge/artifacts/iam_access/
```

**Simulate, never parse.** `collect iam-access` calls `iam:SimulatePrincipalPolicy`:
permissions boundaries, service control policies, explicit `Deny` and `Condition` never
appear in the role's policy document. **`EvalDecision` has four answers and the three
denials need different fixes** — `attrs.denied_by` names the layer (`implicit_deny`,
`explicit_deny`, `permissions_boundary`, `service_control_policy`); collapsing them into
a boolean makes "add the permission" the advice, wrong in three of four cases.
`--catalog-id` is mandatory cross-account; `--resource-arn` changes the question
(`scoped_to_resource`); `--action` should be the action that actually failed. S3 bucket
policy, KMS key policy and Glue resource policy are a **separate** evaluation, and
`iam.access.unresolved` publishes that limit always.

## Output compression — caveman mode

This repository ships the **caveman** ecosystem vendored under `vendor/`, and pins
`full` mode in `.caveman/config.json`. In Claude Code it activates by itself. **Every
other agent — Devin, GitHub Copilot, Codex, or any agent reading this file — must apply
the rules below on its own.** Credit: caveman is by
[Julius Brussee](https://github.com/JuliusBrussee), MIT; provenance in
`vendor/CREDITS.md`; the verbatim ruleset lives in
`vendor/caveman/src/rules/caveman-activate.md`.

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

Where caveman collides with this project, **this project wins**: the
`recommendation:` / `Finding` schema keeps every field; numbers, versions, `rule_id`,
`fact_id`, error strings, SQL, HCL, YAML, JSON and code blocks are copied **verbatim**;
anything the operating contract calls evidence stays anchored. Commit messages, PR
descriptions and code comments are written in normal English. Cloning is the whole
installation — nothing here reaches the network (`tests/test_vendor_caveman.py`).
Durable memory across sessions is `.sparkforge/case.yaml` plus the journal.

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

## Skills AWS oficiais complementares

Eleven AWS operational-procedure skills, adapted from `aws/agent-toolkit-for-aws` (commit
`10b28af8`): `provision-s3-tables-table`, `harden-s3-bucket`, `aws-storage`,
`aws-database`, `aws-serverless`, `aws-iam`, `aws-observability`,
`aws-billing-and-cost-management`, `aws-messaging-and-streaming`, `aws-security` and
`aws-sdk-python-usage`. They are **not dispatchable** — they can mutate live AWS
infrastructure, and each `## Não faz` boundary requires explicit operator confirmation per
write command, unreachable inside a subagent (V-DV-10). Use them for questions about the
**AWS service**; PySpark job diagnosis uses the deterministic SparkForge skills.

## Agentic Engineering Runtime

`sparkforge/agentic/` holds first-class entities (`Claim`, `Evidence`, `Hypothesis`,
`Experiment`, `Decision`, `Unknown`, `Contradiction`, `Objection`, `Rebuttal`), the case
blackboard (`.sparkforge/blackboard/*.jsonl`, append-only, crash-safe), debate,
arbitration, experiment, decision with ADR, memory, budget, security, L0–L5 autonomy and
the execution graph. `sparkforge/agentic/executor/` is the deterministic **producer**.

- `sparkforge arbitrate` runs after `judge` over the **union** of the case facts and
  writes `Claim`/`Evidence`/`Contradiction`/`Unknown`/`Decision` to the blackboard. When
  arbitration does not close it emits a `DebatePlan` with a `debate_gate` verdict
  (`debater`, `experimentar_antes`, `nao_debater`, `unresolved`).
- `sparkforge debate start|next|submit` is an L0 state machine over
  `.sparkforge/debate/<debate_id>/`: it opens only `debater` plans, refuses by name, accepts
  only **re-extracted** evidence and always closes through the `referee`. The host writes
  the arguments (skill `run-debate`, `scripts/run_debate.py`); nothing here calls a
  provider.
- Both executors are **L0**: `applied_changes` is always `false`, and the ADR is a
  proposal with a mandatory `rollback`.
- Every state-changing verb writes a `started`/`finished` pair to
  `.sparkforge/journal.jsonl`; `resume` reads the open ones, `sparkforge journal verify`
  checks the chain.
- **No benchmark of the agentic layer exists, so no gain is claimed** (`CLAUDE.md` rule
  30). Evidence authority tiers: T1 official docs > T2 source/changelog > T3 reproducible
  benchmark > T4 recognised authority >> T5 LLM > T6 conjecture; T5 and T6 are never
  sufficient alone. The `assess_claim` weights are convention, never published as
  measured confidence.

Rules 29 to 33 of `CLAUDE.md` govern this layer and Lake Formation. Status per component:
`docs/agentic-evolution-report.md`. Spec:
`docs/superpowers/specs/2026-09-03-sparkforge-agentic-evolution-design.md`.
