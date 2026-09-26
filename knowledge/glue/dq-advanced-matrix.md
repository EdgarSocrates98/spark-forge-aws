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
status. The validator only consumes metadata and explicitly rejects row-bearing
fields.

The `ADVANCED` path does not accept `PreProcessingQuery`, `NumberOfWorkers`,
`Timeout`, or `AdditionalRunOptions`. These are structural compatibility
signals; this feature does not run Glue, Athena, or Bedrock and does not infer
runtime support from a missing artifact.

Sources: [Glue Data Quality getting started](https://docs.aws.amazon.com/glue/latest/dg/data-quality-getting-started.html),
[Advanced recommendations data protection](https://docs.aws.amazon.com/glue/latest/dg/data-protection-advanced-dq-recommendations.html),
and [Glue release notes](https://docs.aws.amazon.com/glue/latest/dg/release-notes.html).
