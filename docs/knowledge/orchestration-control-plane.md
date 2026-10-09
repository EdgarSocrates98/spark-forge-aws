# Orchestration Control Plane

`sparkforge-aws analyze orchestration --path <inventory.yaml>` normalizes an
explicit inventory of Airflow, Dagster, Step Functions and Control-M. The
report preserves source platform, schedule, sensors, retry/backoff, pools and
concurrency, backfill policy, idempotency and workflow dependencies.

No reliability property is inferred from a task name. Missing dependency,
retry, concurrency, backfill or idempotency declaration is `unresolved`.

Existing source-specific analyzers remain authoritative for raw Airflow DAG,
Step Functions, Control-M and other artifacts. This normalized inventory is a
control-plane bridge into Metadata Graph and blast-radius analysis. It is
read-only: it does not trigger a DAG, state machine, backfill, retry or Control-M
command.
