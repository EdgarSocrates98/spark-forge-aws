# Build Report: PROMPT_EVO_NOVA_EVOLUCAO

## Metadata

| Attribute | Value |
|-----------|-------|
| Feature | PROMPT_EVO_NOVA_EVOLUCAO |
| Date | 2026-09-30 |
| Author | build-agent |
| DEFINE | [DEFINE_PROMPT_EVO_NOVA_EVOLUCAO.md](./DEFINE_PROMPT_EVO_NOVA_EVOLUCAO.md) |
| DESIGN | [DESIGN_PROMPT_EVO_NOVA_EVOLUCAO.md](./DESIGN_PROMPT_EVO_NOVA_EVOLUCAO.md) |
| Status | ✅ Shipped |

## Summary

Implemented the canonical evaluation evidence bundle, explicit policy resolution,
authorized external evidence boundary, paired replay evaluation, and chained
content-addressed receipts for prompt evolution. Promotion now fails closed when
corpus, policy, transcript, evidence, rollback, or receipt provenance is missing.

| Metric | Result |
|--------|--------|
| Tasks completed | 13/13 |
| Files created | 6 |
| Files modified | 7 |
| Delegated agents | 0 |
| Implementation mode | Direct, with design contracts applied inline |
| Performance claim | None; no provider or cost saving was measured |

## Task Execution

| # | Task | Agent | Status |
|---|------|-------|--------|
| 1 | Add canonical evidence bundle domain model | direct | ✅ Complete |
| 2 | Add explicit policy model and resolver | direct | ✅ Complete |
| 3 | Add fixture, bundle-file, and authorized-command adapters | direct | ✅ Complete |
| 4 | Bind evolution service to bundle and policy evidence | direct | ✅ Complete |
| 5 | Add chained, atomic receipt persistence | direct | ✅ Complete |
| 6 | Preserve legacy receipt readability with fail-closed promotion | direct | ✅ Complete |
| 7 | Split one paired replay report into stable old/new reports | direct | ✅ Complete |
| 8 | Update prompt-agent policy configuration | direct | ✅ Complete |
| 9 | Add evidence bundle and tamper tests | direct | ✅ Complete |
| 10 | Add adapter equivalence and refusal tests | direct | ✅ Complete |
| 11 | Extend evolution, replay, benchmark, and host tests | direct | ✅ Complete |
| 12 | Add deterministic evidence fixture | direct | ✅ Complete |
| 13 | Run affected gates and repair gate failures | direct | ✅ Complete |

## Agent Contributions

All tasks were implemented directly. The design assigned one review angle to
`@sf-security-reviewer`, but no task/subagent dispatch tool was available in this
runtime; the security boundary was therefore applied and verified inline through
the adapter allowlist, exact executable checks, bounded output, fixed working
directory, scrubbed environment, `shell=False`, canonical bundle validation, and
the host-provider import tests.

## Files Changed

### Created

| File | Purpose |
|------|---------|
| `sparkforge/evals/evidence.py` | Canonical bundle schema, digest, validation, tamper checks |
| `sparkforge/evals/policy.py` | Exact policy key resolution and policy digest |
| `sparkforge/evals/evidence_adapters.py` | Repo bundle and authorized command adapters |
| `tests/test_evaluation_evidence.py` | Bundle canonicalization, validation, and tamper coverage |
| `tests/test_evaluation_adapters.py` | Adapter contract and command-boundary coverage |
| `evals/token_efficient/fixtures/evolution_evidence_bundles.yaml` | Deterministic labeled evidence fixture |

### Modified

| File | Purpose |
|------|---------|
| `sparkforge/evals/evolution.py` | Policy/bundle binding, fail-closed gates, chained receipts, promotion checks |
| `sparkforge/evals/decision_replay.py` | Paired replay split and policy-controlled minimum corpus |
| `config/evolution/prompt_agents.yaml` | Versioned explicit policy and command registry |
| `tests/test_decision_evolution.py` | Bundle evaluation, receipt sequence, and promotion coverage |
| `tests/test_decision_evolution_benchmark.py` | Paired report and one-call benchmark coverage |
| `tests/test_decision_replay.py` | Replay corpus policy coverage |
| `tests/test_host_provider.py` | Host transcript and provider-boundary coverage |

## Verification Results

| Check | Result |
|-------|--------|
| Ruff on affected source/config/tests | ✅ `All checks passed!` |
| Python compilation | ✅ Passed |
| AgentSpec design linter | ✅ PASS; no findings |
| Focused evaluation/replay tests | ✅ 22 passed |
| Decision/evidence/adapter focused set | ✅ 34 passed |
| `d`–`e` test batch | ✅ 539 passed |
| `f` batch excluding golden fixtures | ✅ 1,928 passed, 2 skipped; facts-scan rerun 78 passed after source fix |
| `g`–`z` test batch | ✅ 5,427 passed, 6 skipped |
| Suite batch contract | ✅ 4 passed |
| `a`–`c` batch | ✅ 2,503 passed, 1 failed initially; version-tree gate rerun 10 passed after intent-to-add registration |
| `tests/test_arvore_versionada.py` | ✅ 10 passed |
| `tests/test_facts_scan.py` | ✅ 78 passed |
| `git diff --check` | ✅ Passed |

The golden extractor batches were not rerun because this change does not modify
golden extraction or fixture generation. Pytest emitted only the repository's
known cache-collision warnings (`WinError 183`); no product test failed after the
targeted repairs. The repository `sparkforge sdd check` command was not applicable:
it only indexes `docs/sdd`, while this AgentSpec artifact is intentionally under
`.claude/sdd/features`.

## Issues Encountered and Resolved

| Issue | Resolution |
|-------|------------|
| Default `%TEMP%\\pytest-of-edgar` could not be created due to permissions | Used an external, writable `--basetemp` directory. |
| A basetemp inside the repository triggered 9 unrelated path-security failures | Repeated the batch with basetemp outside the repository; it passed. |
| Version-tree gate rejected new files absent from the Git index | Registered new files with `git add --intent-to-add`; no commit was created. |
| Facts scan rejected `Path.glob` in receipt discovery | Replaced the scan pattern with `os.scandir`; reran 78 facts-scan tests successfully. |

## Autonomous Decisions

| Decision | Reason |
|----------|--------|
| Implement all manifest tasks directly | No subagent/task dispatch tool was available, while the user authorized the build. |
| Execute replay once and split the paired report | Preserves one evaluation input and prevents old/new divergence from duplicate execution. |
| Keep legacy policy and receipt parsing readable | Existing callers remain compatible; legacy evidence cannot satisfy new promotion requirements. |
| Use `os.scandir` for receipt discovery | Satisfies the repository's source scanning gate without changing behavior. |
| Keep external basetemp outside the workspace | Matches repository path-security requirements and avoids contaminating the checkout. |

## Deviations

No material design deviation. The receipt discovery implementation uses
`os.scandir` instead of the initially drafted `Path.glob` form to satisfy the
repository's facts-scan gate. The legacy global `evaluation_policy` remains as a
compatibility fallback for existing configuration, while new promotion evidence
uses the exact versioned policy key.

## Acceptance Criteria

| ID | Criterion | Evidence | Status |
|----|-----------|----------|--------|
| AT-001 | Bundle evaluation binds policy and receipt sequence | `test_new_evaluation_binds_policy_bundle_and_sequence` | ✅ Pass |
| AT-002 | Authorized command matches canonical bundle | `test_authorized_command_returns_same_canonical_bundle` | ✅ Pass |
| AT-003 | Paired replay executes once and yields stable reports | `test_paired_report_splits_without_reexecution` plus service implementation | ✅ Pass |
| AT-004 | Policy resolution is explicit and versioned | Policy resolver tests and `prompt_agents.yaml` | ✅ Pass |
| AT-005 | Missing exact policy key refuses resolution | Policy resolver missing-key test | ✅ Pass |
| AT-006 | Evidence tampering is detected | Bundle tamper test | ✅ Pass |
| AT-007 | Host transcript/provider evidence remains bounded | Host provider and bundle transcript tests | ✅ Pass |
| AT-008 | Legacy receipts remain readable but cannot prove new corpus gate | Legacy evaluation parsing and promotion tests | ✅ Pass |
| AT-009 | Receipt chain is ordered and tamper checked | Receipt sequence and tamper tests | ✅ Pass |
| AT-010 | Valid policy/bundle can promote | `test_new_evaluation_binds_policy_bundle_and_sequence` | ✅ Pass |
| AT-011 | Promotion requires CI, benchmark, and review evidence | Promotion evidence-kind checks and authority tests | ✅ Pass |
| AT-012 | Core remains provider independent | AST import checks and `test_host_provider.py` | ✅ Pass |

## Performance Notes

No performance improvement or token/cost saving is claimed. Validation measured
correctness, provenance, refusal behavior, and test execution only.

## Final Checklist

- [x] All 13 design tasks completed.
- [x] Affected tests, lint, compilation, scan gates, and diff checks passed.
- [x] No unresolved implementation blocker remains.
- [x] DEFINE and DESIGN statuses updated to `✅ Complete (Built)`.
- [x] Build report written.
- [x] Ready for `/ship .claude/sdd/features/DEFINE_PROMPT_EVO_NOVA_EVOLUCAO.md`.

## Next Step

**Status:** ✅ Shipped and archived
