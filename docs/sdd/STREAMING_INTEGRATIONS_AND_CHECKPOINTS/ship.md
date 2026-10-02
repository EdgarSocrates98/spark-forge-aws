---
sdd: 1
feature: STREAMING_INTEGRATIONS_AND_CHECKPOINTS
phase: ship
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_INTEGRATIONS_AND_CHECKPOINTS/build_report.md
  sha256: "5dcb731deca1810edb1564140185704142c7c9eb9bbc9ef363297e4bf893889e"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, generated_reference, surface_lock, fixture_corpus_gates, fixture_kind_coverage, snippet_measure, reachability_lists, status_numbers_gate, rules_catalog_gates, manifest_rule_count]
deviations: ["collector live, replay temporal e benchmark são N/A + motivo por offline guarantee e ausência de endpoint/credencial"]
---

# STREAMING_INTEGRATIONS_AND_CHECKPOINTS — entrega

Entrega facts/rules/fixtures/analyzer e knowledge para checkpoint, Kafka Connect,
Kafka Streams e OpenLineage. Não afirma saúde live, exactly-once end-to-end ou
lineage completo sem evidência correspondente.
