# Forge Lab runtime fragments

`profiles.yaml` is the declarative profile map used by the CLI plan. The
Compose file is the interactive backend; an optional Testcontainers backend
consumes the same scenario and action plan.

No fragment uses `latest`. Tags come from `lab/versions.yaml`; a real run must
record image digests in `versions.json`. The repository does not download
images, mount the Docker socket, use host networking or pass cloud credentials
implicitly.

Profiles are `core`, `spark`, `kafka`, `streaming`, `flink`, `lakehouse`, `cdc`,
`polaris`, `observability`, `chaos` and `full`. `up`, `down`, `shell` and `gc`
are plan-only unless the operator provides both `--execute` and `--confirm`.
The same guard applies to a mutating `lab run`; `plan` and `verify` never start
services.
