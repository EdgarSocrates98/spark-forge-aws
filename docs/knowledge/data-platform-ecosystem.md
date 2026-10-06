# Data Platform Ecosystem Inventory

`sparkforge-aws analyze platform-ecosystem --path <ecosystem.yaml>` normalizes
Serving/OLAP, ingestion/connectors, AI Data Engineering and optional radar
integrations.

Serving kinds include Trino, Redshift, ClickHouse, Pinot, Druid, DuckDB,
Snowflake and BigQuery. Ingestion kinds include Airbyte, Meltano, Kafka Connect,
Debezium, DMS, JDBC, APIs, SFTP, SaaS, mainframe and SAP. AI kinds include
feature stores, Feast, SageMaker Feature Store, embedding stores, vector
indexes, unstructured stores and models.

Each system needs an owner and source reference. Its Connector Reliability Model
can declare idempotency, checkpointing, retry, DLQ/quarantine, rate limit,
schema contract, freshness SLO and recovery runbook. Missing controls are
`unresolved`; the analyzer does not label a connector reliable.

Beam, DataHub and OpenMetadata are represented as `radar` with
`runtime_dependency: false`. They are integration candidates, not mandatory
runtime dependencies or installed plugins.
