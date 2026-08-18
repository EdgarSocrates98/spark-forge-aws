# Data Lineage and Impact Analysis

Base for edges from code, SQL, DAGs, jobs, tables, buckets and contracts. Lineage is declared relation; it does not prove successful execution.

## Model
Each edge contains source, target, operation, artifact, runtime, owner, confidence and evidence_ref.

## Procedure
- Walk direct consumers from the changed artifact.
- Classify impact in schema, semantics, SLA, security and cost.
- Mark inferred lineage as hypothesis.
- Produce blast radius and validation plan.

## Sources
- https://openlineage.io/docs/
- https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html
