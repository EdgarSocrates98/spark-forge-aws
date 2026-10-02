---
sdd: 1
feature: STREAMING_READ_ONLY_COLLECTORS
phase: ship
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_READ_ONLY_COLLECTORS/build_report.md
  sha256: "fd4d0c41bd525d4e64b9c533971c1429e765af954e08b9766a14072978c732fb"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, offline_manifest, sources_lock, status_numbers, status_numbers_gate, artifact_kind_registry, collector_tests, reachability_lists, fixture_kind_coverage, snippet_measure]
deviations: ["Connect/Streams/OpenLineage live e métricas temporais permanecem N/A + motivo; não existe endpoint AWS universal."]
---

# STREAMING_READ_ONLY_COLLECTORS — entrega

Collector read-only entregue para checkpoint S3, Glue Streaming, Kinesis, MSK e
DMS, com redaction, cache por hash, manifesto, CLI, MCP, testes e documentação.
