# Forge Lab / Digital Twin

The lab is a versioned local topology and evidence factory for reproducing
data-platform incidents across CDC, streaming, batch, lakehouse and
observability boundaries. The complete product contract is
`docs/knowledge/forge-lab-product.md`; this page remains the topology-focused
knowledge entry used by `analyze forge-lab`.

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
Spark Forge analyzer never executes these actions.

The executable product corpus is the Golden 20 in `lab/scenarios/golden.yaml`.
It compiles into allowlisted actions shared by Compose and the optional
Testcontainers backend. `sparkforge lab verify` checks the 11 registry
components, 20 scenarios and 240 action plans offline. The lifecycle CLI
captures artifacts, facts, findings and content-addressed receipts; promotion
to curated fixtures requires review and a valid receipt.

`run`, `up`, `down`, `shell` and `gc` are plan-only unless the operator provides
both `--execute` and `--confirm`. L0–L3 fidelity, result classes and the AWS
validation tier are documented in `forge-lab-product.md`. No local result is a
claim about production capacity, cloud price, IAM semantics or exactly-once.
