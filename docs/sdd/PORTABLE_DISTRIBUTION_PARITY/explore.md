---
sdd: 1
feature: PORTABLE_DISTRIBUTION_PARITY
phase: explore
profile: dev
status: draft
approaches:
  - id: A
    summary: "Add portable lifecycle facades over existing operational core."
    tradeoffs: ["Reuse existing integrate and workspace contracts", "Explicit limitations for legacy persistence"]
  - id: B
    summary: "Copy API Forge runtime and persistence wholesale."
    tradeoffs: ["Broader incompatible domains", "Duplicated operational core"]
chosen: A
---

# Portable distribution parity

User authorized implementing API Forge's portable level in SparkForge AWS.
Baselines: API Forge `07459a2010d51bbf094834aa87bed52b154d2537`, SparkForge
`ab7f02e2423e7c07cc2dbeb982fdc50a2c3f6099`.
Read API portable guide and paths/config/workspace manifests plus SparkForge
case/store, integrate/sources, workspace/manifest, CLI, and sdd-build skill.
Implementation is authorized; formal operator review of these artifacts remains
pending. No approval or `ready` status is inferred.
