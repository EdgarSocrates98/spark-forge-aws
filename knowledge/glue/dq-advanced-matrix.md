# Glue Data Quality recommendation matrix

This matrix is a bounded governance reference for the `BASIC` and `ADVANCED`
recommendation modes consumed by `GLUE_DQ_ADVANCED_GOVERNANCE`. It is not a
claim that every account or Region supports every path.

| Glue runtime | Spark | Python | BASIC | ADVANCED |
|---|---:|---:|---|---|
| 4.0 | 3.3.0 | 3.10 | conditional | conditional |
| 5.1 | 3.5.6 | 3.11 | conditional | conditional |
| 6.0 | 4.1.1 | 3.13 | conditional | conditional |

`ADVANCED` requires Region and service evidence. Its path can sample data for
Athena/Bedrock inference, so governance must preserve classification, source
and inference Regions, sampling-bucket retention, KMS status, and human review
status. The documented sampling reference is workgroup
`glue-dataquality-sampling`, bucket pattern
`aws-glue-dataquality-sampling-<account>-<region>`, and a 14-day lifecycle.
Those values are references, not observations: a manifest that omits them stays
`documented_not_observed` and is not filled by the validator. The validator only
consumes metadata and explicitly rejects row-bearing fields.

Provider documentation claims that advanced recommendation inputs/outputs are
not retained and are not used for training are represented here as
`documented_claim` with source provenance. They do not prove an account's
configuration. Region mismatch is a cross-Region fact; geographic residency is
a separate declared status (`same`, `approved`, `disallowed`, or `unresolved`).
Likewise, aggregate KMS status does not prove key-policy, runtime-role or Lake
Formation authorization evidence. The assessment keeps those three components
independent and requires human review because generated recommendations can
vary; it publishes no numeric variance without repeated measured outputs.

The `ADVANCED` path does not accept `PreProcessingQuery`, `NumberOfWorkers`,
`Timeout`, or `AdditionalRunOptions`. These are structural compatibility
signals; this feature does not run Glue, Athena, or Bedrock and does not infer
runtime support from a missing artifact.

## Fontes

- https://docs.aws.amazon.com/glue/latest/dg/data-quality-getting-started.html (retrieved 2026-09-26)
- https://docs.aws.amazon.com/glue/latest/dg/data-protection-advanced-dq-recommendations.html (retrieved 2026-09-26)
- https://docs.aws.amazon.com/glue/latest/dg/release-notes.html (retrieved 2026-09-26)
