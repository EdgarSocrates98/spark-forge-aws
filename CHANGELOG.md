# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
## [0.6.1] - 2026-10-22

### Fixed

- `_forgecontext` v1.3.2: non-UTF-8 consumer docs (AGENTS.md / CLAUDE.md /
  AGENT_PROTOCOL.md) now refuse with named `FORGE-CONTEXT-CONFLICT` on
  install and uninstall — never a bare `UnicodeDecodeError` mid-write.
- `evals result --run`: run names are validated against a safe pattern
  and resolved under the runs root — `../../` and absolute paths can no
  longer escape `~/.sparkforge_aws/agentic-evals/` (§13.1).

## [0.6.0] - 2026-10-22

### Added

- Install 2.0: `forge-context/v1` registry integration, transactional
  install/uninstall via vendored `_forgecontext` v1.3.1, consumer-doc managed
  blocks, evals classification, `qualified_ids` + `route()` support.

### Fixed

- `_txn_restore` journal path validation; interrupt-safe rollback;
  stale-lock `created_at` fallback (Windows); vendored `_installkit` v1.0.2 +
  `forge_bootstrap` v1.1.1 security backports (userinfo redaction, argv trim,
  empty-stdout smoke).

## [0.5.5] - 2026-10-21

### Changed

- Cycle 13 (graph): Graph Studio vendored update — P0 physics fix (NaN blow-up on hubs/star), scalable visualization modes (overview/explore/full), navigation, inspectors and bounded analysis; post-lf-0023 portal explorer assets re-vendored; security/accessibility/reliability hardening.

## [0.5.3] - 2026-10-20

### Changed
- Cycle 12 portable distribution: `evals_data` packaged corpus +
  `evals/paths.py` resolver (env → cwd → repo-marker → packaged);
  `evals list`; `knowledge list|search` on CLI and MCP (surface lock
  regenerated, 148 tools); `SourcesError` enveloped as named refusal;
  lazy bundle resolution in `playbook`; pyproject marker guards on
  `knowledge_dir`/`catalog_dir`.

## [0.5.2] - 2026-10-18

### Changed
- Portal 2.2 vendored generation (44-asset frontend, telemetry,
  py3.10-safe server); hardened PyPI pipeline (build-once/
  publish-same-artifact, version gate, post-publish verify)

## [0.5.1] - 2026-10-18

### Fixed
- Portal vendored 2.1 final (Cycles 0-6)

## [Unreleased]



## [0.5.6] - 2026-10-21

### Added

- Integrations cycle: governed peer delegation (`sparkforge_aws/delegation/` — discovery, plans, argv-only execution, persisted EvidenceHandoffs, refusal/cycle handling) to data-sentinel-forge and forge-doctor-data; `delegate-specialists` skill + coordinator awareness; `sparkforge-aws delegate` CLI; Windows `.cmd` test fixture shim; surface lock regenerated (61 skills); portal bundle re-vendored with explorer pages.

## [0.5.4] - 2026-10-20

### Changed
- Cycle 12.1: vendored `scripts/forge_bootstrap.py` re-stamped to the canonical ruff-formatted source; `install.windows.sh` added as the Git Bash/MSYS install route; CI gains a `bash -n` gate for it; knowledge list/search tools declared in manifest/capability surfaces with regenerated catalogs and surface lock.

### Fixed

- `doc_manifest._check_links` now verifies `#fragment` anchors on
  tag-pinned repo URLs (they were silently dropped), exempts GitHub line
  refs (`#L10`, `#L10-L20`) and rejects `%5C` backslash escapes.

### Changed

- `pip install sparkforge-aws` section added to the README;
  links/images pinned to `v0.5.0` absolute URLs so the PyPI-rendered
  page resolves.

## [0.5.0] - 2026-10-15

### Added

- Forge Lab emitter producing `forge/BenchmarkResult/v1` receipts over the
  local evaluation/readiness engines (cyc9-04).
- GitHub experience files: CODE_OF_CONDUCT, SUPPORT, issue/PR templates
  (cyc10-02).

### Changed

- Vendored installkit/ui-kit/portal assets refreshed from canonical
  the-forge (cyc8-02, cyc9-10).
