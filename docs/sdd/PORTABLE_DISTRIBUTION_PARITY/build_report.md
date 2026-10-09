---
sdd: 1
feature: PORTABLE_DISTRIBUTION_PARITY
phase: build_report
profile: dev
status: draft
upstream:
  path: docs/sdd/PORTABLE_DISTRIBUTION_PARITY/plan.md
  sha256: "8f8dc16d3808291b6c7bc7012eddac13eda52367169dc4867fcf8e822988c2d5"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_portable_distribution.py -q", exit: 2}
    green: {command: "python -m pytest tests/test_portable_distribution.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_portable_distribution.py::test_persisted_external_lifecycle_cache_and_relocation -q", exit: 1}
    green: {command: "python -m pytest tests/test_portable_distribution.py::test_persisted_external_lifecycle_cache_and_relocation -q", exit: 0}
claims: []
change_id: null
---

Observed red: pytest collection failed with missing
`sparkforge_aws.distribution`; all new behavioral tests were already written.
Verification and review results are appended when actually observed.
Operator signoff remains pending. No formal SDD approval has been invented.

## Verification actually observed

- Initial focused suite: 212 passed, 6 skipped (exit 0).
- Actual external persistence and journal suite: 34 passed (exit 0).
- Expanded focused suite (portable, journal, case, workspace semantic/fingerprint/
  impact, cache, integrate, surface lock and generated reference):
  259 passed, 6 skipped (exit 0).
- Touched-file Ruff: all checks passed (exit 0).
- `python scripts/gen_reference_docs.py`: 285 pages, 5 changed (exit 0).
- `python scripts/check_surface_lock.py`: zero divergences (exit 0).

Expanded tests were regression additions after the initial file-level collection
red; no separate red claim is made for them. Build status draft because formal
operator phase review remains pending, not because tests are blocked.

## Final verification and review

- Final focused regression suite: **263 passed, 6 skipped**, exit 0, 40.76s.
- Final wheel installed in a separate clean environment, launched outside
  checkout with `PYTHONSAFEPATH=1` and `pytest -o pythonpath=`:
  installed provenance + portable + journal + journal/MCP parity goldens:
  **60 passed, 1 skipped**, exit 0, 3.51s.
- Two final builds (`python -m build --no-isolation`) produced identical wheel
  and sdist hashes. Final tested wheel SHA256:
  `225a2a20103f5fe6e540676648f5519b2f3d5399e9d1cad59f93b0a159268749`.
  The final wheel was rebuilt after README whitespace cleanup; the earlier
  wheel/sdist reproducibility run covered the same production code.
- Full `scripts/verify_wheel.py` built two reproducible artifacts and started
  all installed golden tests. Stopped safely with exit 130 at 16% after extended
  runtime; **full golden gate is incomplete and is not claimed green**. It used
  the earlier snapshot; the final wheel proof above includes later review fixes.
- Final touched-file Ruff and `git diff --check`: exit 0.
- `sdd check`: exit 1, only three `phase_out_of_order` refusals because define,
  design and plan intentionally remain draft pending operator phase review.
  Upstream stamps are current; no schema or stale-upstream refusal remains.

Spec review found workspace embedded config validation missing; fixed with
three adversarial tests, reviewer rechecked as conformant (18 portable tests).
Fresh quality review found external journal output digest missing and tilde
loader normalization; fixed and rechecked as conformant (2 targeted tests).
No critical or important findings remained in the reported review.

Known limits: no universal redirect of legacy explicit outputs; default legacy
commands preserve `--repo`; some advanced commands still need checkout assets;
copied project IDs share identity; asset hashes are inventory, not signatures.
See bilingual guide for exact consumer scope and unreleased installation steps.
