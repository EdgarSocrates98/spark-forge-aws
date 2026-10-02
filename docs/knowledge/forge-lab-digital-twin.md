# Forge Lab / Digital Twin

The lab is a versioned local topology for reproducing data-platform incidents
across CDC, streaming, batch, lakehouse and observability boundaries.

Components are declared in `labs/forge-lab/lab.yaml`; the Compose blueprint is
`labs/forge-lab/compose.yaml`. The analyzer is offline:

```bash
sparkforge analyze forge-lab --path labs/forge-lab/lab.yaml
```

The contract includes PostgreSQL, Debezium, Kafka, Flink, Spark, Iceberg REST,
Polaris, MinIO/S3 and Prometheus. Images are intentionally supplied through
operator environment variables so runtime/version compatibility is not invented
by the repository.

Failure scenarios are declarative and require confirmation: broker failure,
partition skew, consumer lag, checkpoint failure, small files, schema evolution
and CDC restart. Each scenario names target, action and expected evidence. The
Spark Forge analyzer never executes these actions; a separate operator-approved
harness may do so later.
