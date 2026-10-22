# Distribution parity — SparkForge AWS

Install-2.0 §8.5 parity matrix for `sparkforge-aws` (dist `sparkforge-aws`,
Hatchling). Three columns: **Checkout** (source tree / `pip install -e .`),
**Wheel local** (wheel built from this branch, installed into a clean venv,
run outside the checkout), **PyPI publicado** (latest released wheel —
`0.5.6`, fetched with `pip download --no-deps sparkforge-aws==0.5.6`; it
predates this branch's packaging fixes).

Legend: ✅ works · ⚠️ works with documented degradation · ❌ broken ·
— not applicable.

| Surface | Checkout | Wheel local | PyPI publicado (0.5.6) |
|---|---|---|---|
| CLI (`sparkforge-aws …`, `sparkforge-aws-tools …`) | ✅ | ✅ console scripts present in clean venv; `install`, `knowledge list`, `rules lookup`, `doctor`, `repair`, `uninstall` all run from a consumer dir | ✅ same entry points |
| Skills | ✅ | ✅ `integrate/bundle/skills` in wheel; install materializes host mirrors | ✅ present in published wheel |
| Agents | ✅ | ✅ `integrate/bundle/agents` in wheel; host mirrors land in the consumer target | ✅ present |
| MCP | ✅ | ✅ `install doctor` exercises the packaged MCP runtime (see Evidence) | ⚠️ entry point exists; not re-verified on published wheel |
| Knowledge | ✅ | ✅ `knowledge list` returns packaged `sparkforge_aws/knowledge` docs under the wheel | ✅ `sparkforge_aws/knowledge` present |
| Rules | ✅ | ✅ `rules lookup --id SF-WASTE-001` resolves from packaged `sparkforge_aws/rules/catalog` | ✅ `rules/catalog` present |
| Protocols | ✅ | ⚠️ `install` writes `AGENT_PROTOCOL.md`; `forge/context/v1` + `forge/context-registry/v1` produced and schema-valid, capabilities populated from the bundled groups — **but** `install/lifecycle._context_manifest` still reads `_REPO_DIR/forge.json` (= `site-packages/` under wheel), so `integrity.files` digests and agentic-sourced fields stay empty until lf-0037's reader wiring lands; `sparkforge_aws/forge*.json` are now packaged so only the reader remains | ⚠️ same degradation, and the published wheel lacks the packaged `forge*.json` payloads entirely |
| Evals | ✅ | ✅ `sparkforge_aws/evals_data/agentic` packaged (runtime corpus; consumer hosts do not execute it) | ✅ `evals_data` present |
| Install | ✅ | ✅ `install --root <consumer> --yes` completes; `integrations.json` ledger + `.mcp.json` + context registry written | ⚠️ installs, but capability manifest degraded (Protocols row) |
| Repair | ✅ | ✅ delete `.mcp.json` → `repair --root` restores it | ⚠️ same path exists; not re-verified on published wheel |
| Uninstall | ✅ | ✅ `uninstall --root` removes managed assets + capability; `install` reinstalls cleanly | ⚠️ same path exists; not re-verified on published wheel |

## Documented degradations / notes

- **Context-manifest integrity fields** (lf-0037 wiring gap, tracked):
  `install/lifecycle._context_manifest` reads `forge.json`/
  `forge.agentic.json`/`manifest.json` only via `_REPO_DIR` (the checkout
  parent — `site-packages/` under `pip install`). This branch ships
  `sparkforge_aws/forge*.json` in the wheel; the reader switch to the
  bundled path (same pattern as `_bundled_dir`) belongs to the
  install/service wiring owned by lf-0037 on `cycle/install-context`.
- `doctor --repo` stays offline by contract (no AWS SDK calls in the core);
  `doctor agentic` verifies the agentic plan against packaged assets.
- `.sparkforge_aws` state resolves under the install root, not the package —
  no checkout path is touched under the wheel (the test's session backstop
  asserts no state dir appears in the repository tree).

## Deliberately not packaged

- Repo-root `manifest.json`: referenced by install context only via the
  checkout path and by dbt/artifact tooling — not an installed-runtime input.
- `parity.yaml`: capability-parity source bound by dev gates/tests; no
  installed code path reads it at runtime.
- `docs/surface.lock.json`: dev-gate lock for surface drift checks
  (`scripts/check_surface_lock.py`), a checkout-only verification surface.

## Evidence

- Wheel isolation test: `tests/test_wheel_isolation.py`
  (`test_wheel_install_lifecycle_outside_checkout`) — builds the wheel,
  installs into a clean venv, proves the import comes from site-packages,
  then runs install → registry/contract → `knowledge list` →
  `rules lookup` → `install doctor` → `doctor`/`doctor agentic` → repair →
  uninstall → reinstall from a consumer dir outside the checkout. Passing
  locally (~190s).
- Wheel contents verified after this branch's packaging fix:
  `sparkforge_aws/{forge.json,forge.agentic.json}`,
  `integrate/bundle/{skills,agents}`, `rules/catalog`, `knowledge`,
  `evals_data`, `portal_assets` all present.
- Published `sparkforge_aws-0.5.6-py3-none-any.whl` (1113 entries) inspected:
  all resource groups present **except** `sparkforge_aws/forge.json` and
  `sparkforge_aws/forge.agentic.json` — the gap this branch closes.
- `scripts/verify_wheel.py` remains the bit-for-bit reproducibility +
  provenance gate (two builds compared, clean-venv run with
  `SPARKFORGE_AWS_CATALOG`/`SPARKFORGE_AWS_KNOWLEDGE` removed and
  `PYTHONSAFEPATH=1`).

## Planned (lf-0037)

Discovery verbs over `.forge/context/` (`rules.search`, `knowledge.search`,
`capabilities.list`, … via `discovery.ops`) are in flight on
`cycle/install-context`. When merged, extend the wheel test to exercise
them and promote the corresponding cells.
