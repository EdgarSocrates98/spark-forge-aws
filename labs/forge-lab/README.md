# Forge Lab / Digital Twin

Forge Lab is a local reproduction blueprint and CLI-first evidence factory for
streaming and batch incidents. The Spark Forge analyzer reads `lab.yaml`; it
does not start Compose, stop a broker, mutate a table or call a provider.

The full operator guide is [`docs/guia/forge-lab.md`](../../docs/guia/forge-lab.md).
The product contract, receipts, oracle and evidence boundary are documented in
[`docs/knowledge/forge-lab-product.md`](../../docs/knowledge/forge-lab-product.md).

The product contract lives in `lab/versions.yaml` and
`lab/scenarios/golden.yaml`. Read the full boundary at
`docs/knowledge/forge-lab-product.md`.

## Inspect topology

```bash
sparkforge-aws analyze forge-lab --path labs/forge-lab/lab.yaml
```

The output includes component dependency order, a deterministic fingerprint,
offline readiness, unresolved declarations and seven topological scenario plans:

- `broker_kill`
- `skew`
- `consumer_lag`
- `checkpoint_failure`
- `small_files`
- `schema_evolution`
- `cdc_restart`

Those seven scenarios describe the topology blueprint in `lab.yaml`. The
versioned executable corpus is the Golden 20 in `lab/scenarios/golden.yaml`,
which is compiled and checked by `sparkforge-aws lab verify`.

## Run locally

1. Choose pinned images in a private `.env` file; do not commit credentials.
2. Review the scenario and its expected evidence.
3. Inspect and compile the scenario first:
   `sparkforge-aws lab verify --repo .` and
   `sparkforge-aws lab plan <scenario> --backend compose --repo .`.
4. Start only the requested profile with `docker compose --profile <profile>
   -f labs/forge-lab/compose.yaml up` or let the CLI plan it.
5. Capture metrics, logs, checkpoints and table metadata.
6. Tear down only after preserving evidence needed for diagnosis.

The Compose file deliberately requires image and credential variables. Image
availability, compatibility, ports and runtime versions remain unresolved until
the operator validates them on the host.

## Product lifecycle

```bash
sparkforge-aws lab doctor
sparkforge-aws lab verify --repo .
sparkforge-aws lab scenarios --json --repo .
sparkforge-aws lab plan iceberg-small-files --backend compose --seed 42
sparkforge-aws lab run iceberg-small-files --backend compose --seed 42
sparkforge-aws lab inspect .sparkforge_aws/lab/runs/<run-id>
sparkforge-aws lab analyze .sparkforge_aws/lab/runs/<run-id>
sparkforge-aws lab compare <run-a> <run-b>
sparkforge-aws lab reproduce .sparkforge_aws/lab/runs/<run-id>/receipt.json
```

Doctor, verify, profiles, scenarios, describe, plan, inspect, analyze, compare
and reproduce are read-only or planning operations. `run`, `up`, `down`,
`shell` and `gc` require both `--execute` and `--confirm` to mutate a local
environment. Runs belong in `.sparkforge_aws/lab/runs/`, never in Git; promotion
requires a reviewed, hash-valid receipt.

The final offline registry verification reported 11 components, 20 Golden
scenarios and 240 compiled actions. It does not claim that Docker images are
available or that a cloud run occurred.
