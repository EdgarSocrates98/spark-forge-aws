# Platform Intelligence Graph v1

Spark Forge accepts a local, declarative metadata graph for a Data Platform
Control Plane. The contract is `contracts/platform-graph-v1.schema.json` and the
offline analyzer is:

```bash
sparkforge-aws analyze platform-graph \
  --path platform-graph.yaml \
  --changed-node postgres.orders \
  --changed-attribute primary_key \
  --direction downstream \
  --max-depth 5
```

The same operation is exposed as `sparkforge_aws_analyze_platform_graph`.

## Contract

Nodes represent datasets, jobs, runs, producers, consumers, contracts, owners,
SLOs, schemas, dashboards, metrics, models, services, topics, streams, tables,
catalogs, orchestrators, features and vector indexes. `kind` is the canonical
entity class; `subtype` identifies a concrete technology such as Kafka, Flink,
Spark, Iceberg, dbt, Airflow, Glue, EMR or Athena.

Edges are directed and explicit. IDs are the only join key. `evidence` and
`source_system` remain attached to the graph. Duplicate conflicting records and
missing endpoints are returned in `unresolved`.

## Impact semantics

`downstream` follows `source → target`, `upstream` follows the reverse and `both`
does both. `direct` is one hop; `transitive` is greater than one hop; `paths`
contains the bounded route and relation list. Missing node or attribute is a
named unresolved condition. The analyzer never resolves a relationship by label,
never calls AWS/Kafka/catalog APIs and never claims blast radius beyond explicit
edges.

## Integration boundary

Future adapters may emit `GraphFragment` records from Glue Catalog, OpenLineage,
dbt, Airflow, Dagster, Kafka, Flink, Iceberg, OpenTelemetry or cloud APIs. They
must provide explicit IDs and evidence; composition must preserve conflicts,
freshness and unresolved facts.
