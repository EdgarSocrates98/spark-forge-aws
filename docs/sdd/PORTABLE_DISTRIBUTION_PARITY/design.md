---
sdd: 1
feature: PORTABLE_DISTRIBUTION_PARITY
phase: design
profile: dev
status: draft
upstream:
  path: docs/sdd/PORTABLE_DISTRIBUTION_PARITY/define.md
  sha256: "125d93fb5a26ac3e9cc55a042851d1689bdb762855c4f38a1a6e5ce56dd3a51d"
files:
  - {path: tests/test_portable_distribution.py, action: create, reason: "Behavioral portable contracts first"}
  - {path: sparkforge_aws/distribution/config.py, action: create, reason: "Strict bounded settings"}
  - {path: sparkforge_aws/distribution/paths.py, action: create, reason: "Namespaced operational paths"}
  - {path: sparkforge_aws/distribution/service.py, action: create, reason: "Read-only lifecycle and scoped locality"}
  - {path: sparkforge_aws/distribution/cli.py, action: create, reason: "Additive CLI facade"}
  - {path: sparkforge_aws/distribution/__init__.py, action: create, reason: "Package marker"}
  - {path: sparkforge_aws/workspace/portable.py, action: create, reason: "Explicit portable discriminator and discovery"}
  - {path: sparkforge_aws/workspace/manifest.py, action: modify, reason: "Dispatch portable schema without weakening legacy"}
  - {path: sparkforge_aws/case/store.py, action: modify, reason: "Wire external state and preserve default legacy behavior"}
  - {path: sparkforge_aws/decision/cache.py, action: modify, reason: "Wire cache override"}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "Register additive verbs"}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "Wire CLI artifact cache"}
  - {path: sparkforge_aws/adapters/mcp.py, action: modify, reason: "Wire MCP artifact cache without new tools"}
  - {path: sparkforge_aws/journal/record.py, action: modify, reason: "Resolve external case anchor"}
  - {path: sparkforge_aws/lab/evidence.py, action: modify, reason: "Wire lab run state"}
  - {path: docs/guides/SPARKFORGE_AWS_PORTABLE.md, action: create, reason: "English operating guide"}
  - {path: docs/guides/SPARKFORGE_AWS_PORTABLE.pt-BR.md, action: create, reason: "Portuguese operating guide"}
  - {path: README.md, action: modify, reason: "Link guide"}
decisions:
  - id: D1
    choice: "Portable manifests contain relative roots and a stable opaque project ID."
    rejected: ["Absolute roots preventing relocation", "Identity shared across independently initialized repos"]
    rollback: "Revert feature; portable manifests are additive."
  - id: D2
    choice: "Portable workspace discriminator explicitly allows external relative roots; legacy loader remains confined."
    rejected: ["Implicit allow-any path traversal in old manifests"]
    rollback: "Remove portable dispatch; original schema unchanged."
  - id: D3
    choice: "Read-only locality never hashes consumer source contents."
    rejected: ["Eager graph inference during status"]
    rollback: "Use existing explicit graph commands."
covers:
  - {part: "portable lifecycle", acceptance: [AC1, AC2, AC3, AC4, AC5, AC6, AC7]}
---

Pending operator review. Inventory hashes report observed asset bytes, not trusted
authorship. Host setup reuses existing `integrate`/`detach` commands.
