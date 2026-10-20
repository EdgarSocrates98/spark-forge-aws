# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
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
