---
sdd: 1
feature: PORTABLE_DISTRIBUTION_PARITY
phase: define
profile: dev
status: draft
upstream:
  path: docs/sdd/PORTABLE_DISTRIBUTION_PARITY/explore.md
  sha256: "0d59b8c071c1f56fd9e137c559d8b74f7c2303be55facd9927e1c129b1dd1938"
hypothesis:
  claim: "Portable lifecycle and scoped workspaces work offline without copying installation assets into consumers."
  prediction: "Behavioral portable tests pass with read-only inspection, relocation, isolated state and named refusals."
  experiment: "New adversarial pytest module plus installed-wheel verification outside checkout."
acceptance:
  - id: AC1
    statement: "Read-only offline inspection and minimal idempotent initialization."
    verified_by: {kind: test, ref: "tests/test_portable_distribution.py::test_read_only_hostless_and_minimal_init"}
  - id: AC2
    statement: "Stable project identity on relocation and isolated external state."
    verified_by: {kind: test, ref: "tests/test_portable_distribution.py::test_relocation_and_isolated_state"}
  - id: AC3
    statement: "Strict configuration with explicit override precedence."
    verified_by: {kind: test, ref: "tests/test_portable_distribution.py::test_config_precedence_and_strict_errors"}
  - id: AC4
    statement: "Bounded discovery covers nested modules and Git worktrees without opening metadata."
    verified_by: {kind: test, ref: "tests/test_portable_distribution.py::test_discovery_bounded_nested_and_worktree"}
  - id: AC5
    statement: "Declared external repositories and missing relationships yield scoped locality and unresolved."
    verified_by: {kind: test, ref: "tests/test_portable_distribution.py::test_workspace_external_missing_and_locality"}
  - id: AC6
    statement: "Collision and symlink refusals preserve manifests and legacy confinement."
    verified_by: {kind: test, ref: "tests/test_portable_distribution.py::test_manifest_collision_symlinks_and_legacy_confinement"}
  - id: AC7
    statement: "Additive distribution/workspace/context verbs preserve MCP surface."
    verified_by: {kind: test, ref: "tests/test_portable_distribution.py::test_cli_additive_surface"}
success:
  - id: SC1
    metric: "Portable behavioral failures"
    source: "python -m pytest tests/test_portable_distribution.py -q"
out_of_scope: ["API-specific autonomous runtime", "Host activation duplication", "Automatic state migration", "Trusted asset signatures"]
unknowns: []
case_id: null
change_kinds: [disk_read, tool_or_verb]
---

Config controls portable locality resolution only; no claim that existing
analyzers consume this new settings schema. HOME and CACHE overrides are wired
to operational central case/state/cache consumers; custom explicit output paths
remain explicit. Limitations are documented in the portable guide.
