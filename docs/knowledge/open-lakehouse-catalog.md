# Open Lakehouse / Catalog Engineering

Spark Forge represents catalog topology as a local contract before any live
connector is added. The contract is
`contracts/lakehouse-catalog-v1.schema.json`; the analyzer is:

```bash
sparkforge analyze lakehouse-catalog --path catalog.yaml
```

It models Glue Catalog, Iceberg REST, Polaris, S3 Tables, Lake Formation and
future Unity/Nessie identities, plus Spark, Flink, Trino, Athena, DuckDB,
Redshift, ClickHouse, Pinot, Druid, Snowflake and BigQuery engine identities.
Those names are types, not proof of installed versions or compatibility.

`bindings` must state catalog, engine, tables, access and evidence. A binding
with a missing reference becomes `unresolved`; the analyzer does not join by
table name. Capabilities are declared observations and require a source. There
is no live protocol negotiation in this verb.

Secret-bearing keys (`password`, `token`, `secret`, access keys, credentials and
private keys) are refused. Use `endpoint_ref: env:NAME` or an opaque reference;
do not commit URLs containing query credentials.

Future live adapters should emit graph fragments with catalog identity, runtime
version, evidence and freshness. They must preserve divergence between Glue,
REST and service-specific views instead of selecting one silently.
