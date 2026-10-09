---
sdd: 1
feature: PORTABLE_DISTRIBUTION_PARITY
phase: plan
profile: dev
status: draft
upstream:
  path: docs/sdd/PORTABLE_DISTRIBUTION_PARITY/design.md
  sha256: "31825a5e6014391e301b180516af9308acf31214bc8a7c239fcaf2f61dc648ea"
tasks:
  - id: T1
    files: [tests/test_portable_distribution.py, sparkforge_aws/distribution/config.py, sparkforge_aws/distribution/paths.py, sparkforge_aws/distribution/service.py, sparkforge_aws/distribution/cli.py, sparkforge_aws/workspace/portable.py, sparkforge_aws/case/store.py, sparkforge_aws/adapters/cli.py]
    covers: [AC1, AC2, AC3, AC4, AC5, AC6, AC7]
    test: {path: tests/test_portable_distribution.py, name: test_read_only_hostless_and_minimal_init}
  - id: T2
    files: [sparkforge_aws/journal/record.py, tests/test_portable_distribution.py]
    covers: [AC2]
    test: {path: tests/test_portable_distribution.py, name: test_persisted_external_lifecycle_cache_and_relocation}
---

T1: write behavioral portable contracts; run whole module and observe missing
production module during collection. Implement strict manifests/settings,
central operational paths, bounded discovery and additive commands. Run same
module, then existing state/workspace/cache/integrate regressions, reference and
surface gates, and wheel verification. Document actual output and limits.

Deviation: tests preceded implementation, but artifacts were recorded during
the implementation session rather than a formally reviewed ready plan. This
remains explicit draft; no claim of a completed formal SDD lifecycle.

T2: quality review exposed missing output digest for external HOME state. Extend
the persisted lifecycle test with the actual case-file hash, observe assertion
failure, then map owned logical state references through central state paths.
Arbitrary external outputs must remain unreadable to the journal.
