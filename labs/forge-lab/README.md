# Forge Lab / Digital Twin

Forge Lab is a local reproduction blueprint for streaming and batch incidents.
The Spark Forge analyzer reads `lab.yaml`; it does not start Compose, stop a
broker, mutate a table or call a provider.

## Inspect topology

```bash
sparkforge analyze forge-lab --path labs/forge-lab/lab.yaml
```

The output includes component dependency order, a deterministic fingerprint,
offline readiness, unresolved declarations and seven scenario plans:

- `broker_kill`
- `skew`
- `consumer_lag`
- `checkpoint_failure`
- `small_files`
- `schema_evolution`
- `cdc_restart`

## Run locally

1. Choose pinned images in a private `.env` file; do not commit credentials.
2. Review the scenario and its expected evidence.
3. Start only the requested profile with `docker compose --profile <profile>
   -f labs/forge-lab/compose.yaml up`.
4. Capture metrics, logs, checkpoints and table metadata.
5. Tear down only after preserving evidence needed for diagnosis.

The Compose file deliberately requires image and credential variables. Image
availability, compatibility, ports and runtime versions remain unresolved until
the operator validates them on the host.
