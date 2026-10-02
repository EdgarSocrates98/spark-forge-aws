# Data Observability / SRE

Use `sparkforge analyze data-observability --path <artifact.yaml>` over an
exported OTel-like measurement bundle. The contract keeps indicator, unit,
operator, target, objective and window together. It reports sample count,
compliance, fail count and error-budget consumption only from measurements in
the artifact.

Supported indicator labels include freshness, completeness, latency, lag,
throughput and availability. Labels do not create measurements. A missing or
unit-incompatible sample is `unresolved`; the analyzer never turns it into
zero, healthy or met.

Incidents with explicit ISO timestamps receive MTTR seconds. Open incidents or
invalid timestamps stay unresolved. Dependency status and blast radius are
preserved context, not root-cause findings. Live Prometheus, CloudWatch,
OpenTelemetry Collector and pager systems require separate, approved
collectors.
