# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
## [0.7.8] — 2026-11-13

### Changed

- Unified platform release: version bump + VERSION_DUMP.unified-release.json.

## [Unreleased]

### Changed

- install wave-03 (cycle-16.1): recibos e health docs agora carregam o
  bloco `lifecycle` (`forge/InstallLifecycle/v1`) derivado de
  `status`+`verification`+checks — `planned|blocked|failed|applied|
  partially_applied|verified|unverified|ready|certified`. O `status`
  grosso do recibo segue inalterado (enum do InstallReceipt/v1).
- `managed_files` do recibo de install reporta a acao real por arquivo
  (`created|updated|unchanged|adopted|removed`) + `counts` agregados —
  antes todo arquivo saia como `written` (o plano repetido como fato).
- Reinstall e explicitamente idempotente: a segunda execucao marca
  managed_files como `unchanged`, `counts.written: 0` e nao reescreve
  bytes (coberto por teste de hash antes/depois).
- Docs do escopo `user` (integrate/detach/status/doctor) ganham `status`
  + `lifecycle` derivados — `status --scope user` reporta `unverified`
  honesto (drift do ledger do HOME nao e medido por esse verbo).
- CLI: o exit code vem do `lifecycle.state` — `status` healthy e
  `install --scope user` bem-sucedidos saem 0 (saíam 1); recusas de
  aprovacao saem 1 com estado `blocked`; `declined` (fora do enum do
  recibo) virou `failed` + check BLOCKED; `mcp verify` com handshake PASS
  sai 0 (saía 1 — doc de check nao usa o vocabulario `completed`).
- `repair --dry-run` e `uninstall --dry-run` reportam `status: planned`
  + `lifecycle: planned` — antes diziam `completed`/`verified` sem ter
  escrito nada.
- Health docs (`status`, `install doctor`) carregam o mesmo bloco
  `lifecycle` — healthy→ready, degraded→partially_applied,
  broken→failed, unverified→unverified.
- UI: a saida legivel mostra a linha `lifecycle` e colore
  `applied`/`partially_applied` como alerta.
- Docs: quickstart documenta a tabela de estados do lifecycle;
  update-and-repair/uninstall/troubleshooting alinhados; mcp.md
  corrigido (`install --update` nao existe — reinstall idempotente);
  quickstart usava `sparkforge-aws doctor` (verbo agêntico) onde queria
  `install doctor` (health da instalação).

- install-2.1 wave-02 (cycle-16): `forge.json` declara
  `installation_kind: content`, a superficie `install`
  (operations/flags/hosts/scopes/profiles/`--yes`) e `depends_on: []` —
  copiados verbatim ao manifesto registrado
  (`forge/InstallationManifest/v1`), incluindo `depends_on` vazio.
- Ponteiros de knowledge gerados pelo install agora vivem em
  `knowledge/sparkforge-aws/<rel>` (subdir proprio do forge), nao mais na
  raiz generica `knowledge/` — evita colisao entre forges na mesma arvore.
  Migracao honesta: stubs antigos gerenciados saem do disco e do
  manifesto; arquivo editado pelo usuario fica com recusa nomeada;
  arquivo de outra forge nunca e tocado.
- `--profile` vira matriz explicita (`PROFILE_COMPONENTS`): `minimal` =
  config+MCP+docs; `recommended` e `full` instalam o mesmo conjunto de
  assets hoje. `_want_file` filtra por kind, entao `--components
  knowledge|rules|evals` passa a ter efeito proprio.
- Re-vendor installkit 1.0.6 + forge bootstrap/UI do the-forge.

## [0.7.7] - 2026-11-12

SDD consolidation release: `federated-schemas` CI job consumes canonical
schemas from the-forge via `FORGE_SDD_SCHEMA_DIR`, closing the wave-5
federation loop on the AWS provider.

## [0.7.6] - 2026-11-12

Cycle 2.7 patch release: federated SDD contracts and adapters, forge-context kind taxonomy, universal Obsidian export verbs, portal and install UX improvements, provider context-registry wiring, CI hardening and generated-artifact refresh.


## [0.7.5] — 2026-11-10

### Fixed

- Published the Cycle 2.7 Windows command-environment compatibility fix.

## [0.7.4] — 2026-11-04

### Changed

- Prepared the release after `0.7.3` was already present on PyPI.

## [0.7.3] — 2026-11-04

### Fixed

- Synced the hardened Forge Portal runtime and refreshed bundled portal assets.

## [0.7.2] — 2026-11-04

### Fixed
- Windows integration, installation health state and claim-drift evidence.

## [0.7.1] — 2026-10-23

### Fixed
- patch — manifest/agentic/plugin.json versions synced; no behavior change



## [0.7.0] - 2026-10-23

### Fixed

- `ui._has_vcs_root`/`_cli_argv`: stray `forge.json` in an ancestor no
  longer marks a project root — requires sibling `pyproject.toml`.
  Regression tests added; changelog ordering restored.

## [0.6.3] - 2026-10-23

### Security

- Vendored `_installkit` 1.0.4: unsafe ledger keys surfaced in
  `status().drift.unsafe`; `doctor` marks them non-repairable.

## [0.6.2] - 2026-10-23

### Fixed

- `_forgecontext` v1.3.3 + `_installkit` v1.0.3 (vendored): `repair_context`
  reports malformed capability files per-file instead of crashing with an
  untyped `KeyError`; context/install locks carry a unique token so
  `__exit__` never unlinks a foreign lock and a lost reclaim race is a
  named `FORGE-CONTEXT-LOCKED`/`FORGE-INSTALL-LOCKED`; poisoned journals
  quarantine and report instead of wedging every later context op; asset
  and ledger paths are validated before touching disk — `..`, absolute,
  drive or backslash refs are refused as `FORGE-INSTALL-UNSAFE-PATH`,
  never written or unlinked outside the install root; `_atomic_write`
  preserves the existing file's mode.
- `integrate`: `knowledge/<rel>` references extracted from emitted docs
  now discard traversal refs (`..`, absolute, drive, backslash) at
  extraction AND at the write layer — a doc mentioning
  `knowledge/../../x.md` can no longer create or delete files outside
  the install root. `apply_files`/`remove_owned` reject unsafe manifest
  keys as named `path_fora_da_raiz` refusals.
- `install --scope user` parity: `_register_context` is a no-op at user
  scope — `~/.forge/` is account-level state, matching the sibling forges
  and the documented model.
- A `BLOCKED` check on the mandatory context-registry component now marks
  the receipt `failed` (nonzero exit) instead of `completed`.

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

## [0.5.6] - 2026-10-21

### Added

- Integrations cycle: governed peer delegation (`sparkforge_aws/delegation/` — discovery, plans, argv-only execution, persisted EvidenceHandoffs, refusal/cycle handling) to data-sentinel-forge and forge-doctor-data; `delegate-specialists` skill + coordinator awareness; `sparkforge-aws delegate` CLI; Windows `.cmd` test fixture shim; surface lock regenerated (61 skills); portal bundle re-vendored with explorer pages.

## [0.5.5] - 2026-10-21

### Changed

- Cycle 13 (graph): Graph Studio vendored update — P0 physics fix (NaN blow-up on hubs/star), scalable visualization modes (overview/explore/full), navigation, inspectors and bounded analysis; post-lf-0023 portal explorer assets re-vendored; security/accessibility/reliability hardening.

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

## [0.5.0] - 2026-10-15

### Added

- Forge Lab emitter producing `forge/BenchmarkResult/v1` receipts over the
  local evaluation/readiness engines (cyc9-04).
- GitHub experience files: CODE_OF_CONDUCT, SUPPORT, issue/PR templates
  (cyc10-02).

### Changed

- Vendored installkit/ui-kit/portal assets refreshed from canonical
  the-forge (cyc8-02, cyc9-10).
