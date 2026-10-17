# PyPI patch plan — sparkforge-aws

Cycle 11.2 (P1-004 + P1-006). Prepared for maintainer approval; nothing here
publishes, tags or uploads anything.

## Current state (audited 2025-… cycle 11.2)

| Signal | Value |
|---|---|
| PyPI published | `sparkforge-aws 0.5.0` (only release) |
| `pyproject.toml` | `0.5.0` — aligned |
| Git tag / GitHub release | `v0.5.0` — aligned |
| `requires-python` | `>=3.10` |
| CI matrix before this PR | `["3.10","3.11","3.12"]` (schedule/dispatch), `["3.11"]` on PR |
| Classifiers before this PR | 3.10 / 3.11 / 3.12 |

**No version drift**: PyPI = pyproject = tag = GitHub release.

## What changes in this PR

1. **CI matrix** (`ci.yml`, `test` job): schedule/dispatch leg now
   `["3.10","3.11","3.12","3.13","3.14"]` — every minor inside
   `requires-python`. PR fast path unchanged at 3.11.
2. **Locks**: `locks/py3.13.txt` + `locks/py3.14.txt` generated with
   `python scripts/gen_lock.py` (uv pip compile, `x86_64-manylinux_2_28`,
   `--only-binary :all:`); `PYTHON_VERSIONS` extended — `test_supply_chain.py`
   requires lock ↔ matrix parity.
3. **Classifiers**: added `Python :: 3.13`, `Python :: 3.14`.
4. **project.urls**: added `Documentation` (GUIA_DE_USO.md) and `Changelog`
   (CHANGELOG.md) — both files exist on `main`; PyPI 0.5.0 page lacks both.

## Proposed next release: `0.5.1` (patch)

Rationale: metadata/classifier corrections + CI coverage. No code, API,
dependency or rule change; patch per repo convention.

### Provenance checklist for the maintainer

- [ ] Confirm CI green on this PR (PR leg) **and** trigger/await a
      `workflow_dispatch` or nightly run for the 5-version matrix.
- [ ] `python scripts/gen_lock.py --check` → `OK: 5 locks`.
- [ ] `python -m pytest tests/test_supply_chain.py tests/test_ci_workflow.py -q`.
- [ ] Review `docs/gates-por-mudanca.md` row coverage for this diff.
- [ ] Bump `version = "0.5.1"` in `pyproject.toml` at release time.
- [ ] Tag `v0.5.1` after merge; publish via `publish-pypi.yml` /
      `release.yml` per the existing release flow.
- [ ] Verify PyPI page shows 5 Python classifiers + new URLs.

## Local smoke evidence (this PR)

- Interpreters: system `python3.12` (3.12.3); uv-managed 3.10.21, 3.11.16,
  3.13.15, 3.14.7.
- `uv pip install -e .` on **3.13** and **3.14**: clean resolve;
  `sparkforge-aws --version`/`--help` OK on both.
- `python -m build --wheel` on **3.13**: `sparkforge_aws-0.5.0-py3-none-any.whl`
  built successfully.
- `pytest` smoke subset (graph/parity/surface tests) passes on 3.13 and 3.14.

## Blockers

None. All five versions resolve and pass local smoke; no version was excluded.
