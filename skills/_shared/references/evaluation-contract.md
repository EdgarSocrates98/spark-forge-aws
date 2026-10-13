# SparkForge skill contract: offline evaluation

Each skill owns `evals/evals.json` using the `skill-creator` schema. Cases are
realistic prompts, not claims that a model was run. They must describe an
expected evidence-first answer and include assertions for:

- the skill's trigger and primary SparkForge verb or artifact;
- anchored evidence and runtime/source provenance;
- explicit `unresolved` handling for missing evidence;
- recommendation fields when a change is proposed;
- validation and rollback.

`python scripts/check_skill_evals.py` validates coverage and path safety.
`python scripts/run_skill_evals.py --offline` runs deterministic contract checks
only: it does not call a provider, AWS, or an MCP server. A provider benchmark
needs a separately recorded transcript, baseline, and grader; no performance or
token gain is inferred from this offline gate.
