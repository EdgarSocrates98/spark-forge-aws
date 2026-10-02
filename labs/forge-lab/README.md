# Forge Lab / Digital Twin

Forge Lab is a local reproduction blueprint and CLI-first evidence factory for
streaming and batch incidents. The Spark Forge analyzer reads `lab.yaml`; it
does not start Compose, stop a broker, mutate a table or call a provider.

The product contract lives in `lab/versions.yaml` and
`lab/scenarios/golden.yaml`. Read the full boundary at
`docs/knowledge/forge-lab-product.md`.

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

## Product lifecycle

```bash
sparkforge lab doctor
sparkforge lab scenarios --json
sparkforge lab plan kafka-consumer-lag-001
sparkforge lab run kafka-consumer-lag-001
```

The commands above are read-only/planning commands. `up`, `down`, `shell` and
`gc` require both `--execute` and `--confirm` to mutate a local environment.
Runs belong in `.sparkforge/lab/runs/`, never in Git; promotion requires a
reviewed, hash-valid receipt.
