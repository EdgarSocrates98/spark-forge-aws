# Platform Intelligence Evals

`evals/platform_intelligence/suite.yaml` is the seed contract for the Data
Platform Control Plane. Each case carries expected facts, expected findings,
forbidden findings, unresolved blind spots, architecture constraints, required
evidence, routing and economy limits.

Validate shape offline:

```bash
python scripts/check_platform_eval_contract.py \
  --path evals/platform_intelligence/suite.yaml
```

Quality axes are fact recall, finding precision, false-positive/negative rate,
unresolved recall, evidence recall, routing accuracy and architecture
conformance. Economy axes are context bytes, tool calls, elapsed time and
provider tokens only when a host transcript supplies them. Bytes never convert
to provider tokens by formula; without transcript the result is
`unresolved_without_host_transcript`.

The checked-in pack is a seed, not a production corpus and makes no recall,
precision or cost claim. Expansion requires labeled real cases, per-domain
holdout, expected evidence review and reproducible before/after baselines.

## Prompt coverage

The Control Plane now has a deterministic contract for the major domains
described by `prompt_evo_nova_janela.md`:

| Prompt area | Delivered surface | Boundary kept explicit |
| --- | --- | --- |
| Metadata graph, lineage and impact | `analyze platform-graph`; explicit nodes, edges, fingerprints and bounded downstream/upstream impact | No lineage is inferred from names or unregistered systems |
| Forge Lab and digital twin | `analyze forge-lab`; topology, scenarios, confirmation gates and environment-variable image references | No Docker, broker, database or cloud process is started automatically |
| Open Lakehouse and catalog | `analyze lakehouse-catalog`; Glue, Iceberg REST, Polaris, S3 Tables, Lake Formation, Unity and Nessie contract inventory | No credential discovery, live negotiation or catalog mutation |
| DuckDB microscope | `analyze duckdb-microscope`; read-only SQL bundle, relations, indexes, pragmas and query-plan observations | Mutating SQL and implicit execution are refused |
| Analytics engineering and dbt | `analyze dbt-artifacts`; manifest, catalog, run-results, dependencies, tests and exposures | Missing catalog/run evidence remains unresolved |
| Data observability and SRE | `analyze data-observability`; declared SLO compliance, error budget, incidents, MTTR and dependency blast radius | Open or missing measurements do not become healthy by assumption |
| Orchestration | `analyze orchestration`; normalized Airflow, Dagster, Step Functions and Control-M workflow controls | No scheduler trigger, pause, retry or deployment is performed |
| Serving and OLAP | `analyze platform-ecosystem`; Trino, Redshift, ClickHouse, Pinot, Druid, DuckDB, Snowflake and BigQuery inventory | Connectivity and runtime performance require supplied evidence |
| Ingestion and CDC | `analyze platform-ecosystem`; Airbyte, Meltano, Kafka Connect, Debezium, DMS, JDBC, API, SFTP, SaaS, mainframe and SAP inventory | Source-specific live credentials and CDC execution are outside offline analysis |
| AI/ML data platform | `analyze platform-ecosystem`; feature stores, Feast, SageMaker Feature Store, embeddings, vector indexes, unstructured data and models | Feature freshness, vector recall and model quality need declared measurements |
| Radar and interoperability | Ecosystem radar records Beam, DataHub and OpenMetadata as explicit runtime dependencies | Radar is inventory, not an adoption or compatibility claim |
| Quality and economy | `evals/platform_intelligence/suite.yaml`; facts, findings, forbidden findings, unresolved blind spots, evidence, routing, architecture and economy axes | The checked-in 8-case pack is a seed; it publishes no production recall, precision or savings |

All surfaces preserve the repository evidence contract: absent evidence is
reported as `unresolved`, execution remains offline by default, and any live
adapter must add its own artifact, permission boundary, provenance and
validation gate before it can be treated as platform capability.
