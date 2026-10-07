# Forge Lab Product Contract

Forge Lab is an evidence factory for Spark Forge. It creates reproducible
scenario plans, lets an explicitly enabled host run them, captures machine
readable artifacts, and compares observations with an independent oracle. It
is not an AWS emulator and a local result never becomes an AWS performance
claim.

## Delivered contract

| Prompt area | Repository surface | Guarantee |
| --- | --- | --- |
| Foundation and fidelity | `lab/versions.yaml`, `sparkforge_aws/lab/contract.py` | One registry, no `latest`, L0/L1/L2/L3, `lite/standard/deep`, profiles and explicit `does_not_prove` |
| Compose and Testcontainers | `labs/forge-lab/compose.yaml`, `sparkforge_aws/lab/runtime.py` | Same scenario/action plan; Compose is interactive, Testcontainers is optional CI backend |
| Spark, Kafka, Flink and Iceberg | Compose profiles plus Golden 20 topology | Real-engine plan is L1; image availability, digest and runtime compatibility stay unresolved until host validation |
| Catalogs and object stores | Iceberg REST/Polaris profiles and compatibility plan | Fast/platform catalog and multi-engine operations are declared, not silently measured |
| CDC | PostgreSQL/Debezium/Kafka profile and LAB-013–016 | Snapshot, delete/tombstone, restart/duplicate and incompatible schema scenarios are represented |
| Scenario DSL | `lab/scenarios/golden.yaml`, `sparkforge_aws/lab/scenario.py` | Scenario is data; compiler emits reusable allowlisted actions, not shell scripts |
| Fault engine | `sparkforge_aws/lab/faults.py`, Toxiproxy profile | Network/process/compute/application/data faults require confirmation; no fault executes during analysis |
| Dataset/workload | `sparkforge_aws/lab/generators.py`, `workload.py` | Seed, schema, cardinality, skew, late events and duplicates are deterministic and separate from arrival rate/bursts |
| Observability | `lab/probes/catalog.yaml`, Prometheus/OTel services | Prometheus, Flink REST, Spark progress, Kafka API, Iceberg and CDC are machine-readable sources; Grafana is UI only |
| Artifacts and receipts | `sparkforge_aws/lab/evidence.py` | Run layout, SHA-256 artifacts, versions, facts, findings, assertions and content-addressed receipt |
| Oracle | `sparkforge_aws/lab/oracle.py` | Expected facts/findings/forbidden/unresolved are authored outside the analyzer; actual cannot generate expected |
| Curated fixtures | `promote-fixture --reviewed` | Promotion requires a valid receipt and explicit review |
| Golden 20 | `lab/scenarios/golden.yaml` | LAB-001 through LAB-020 cover small files, skew, spill, lag, hot partition, recovery, watermark/state, Flink, CDC, Iceberg, sink propagation and latency |
| Chaos/blast radius | `faults.py`, `compatibility.py` | Fault plans and predicted-vs-observed impact comparison are available without claiming a live result |
| Multi-engine equivalence | `build_equivalence_plan()` | Spark/Flink/Trino/DuckDB read/write/schema-evolution operations are declared; compatibility remains `declared_unmeasured` until a run receipt exists |
| AWS validation tier | `sparkforge_aws/lab/aws.py` | L3 requires region, owner, run id, TTL, budget, prefix, tags and confirmation; offline core never provisions or cleans AWS |
| Agentic integration | CLI plans and receipts | Agents can request an experiment plan; starting containers is never an implicit agent action |
| CI/hardening | Scenario schema, run/receipt schemas, registry and deterministic plans | Fast fixtures and future L1/nightly/matrix tiers share contracts; no absolute performance inference |

## CLI

```bash
sparkforge-aws lab doctor
sparkforge-aws lab profiles
sparkforge-aws lab scenarios --json
sparkforge-aws lab describe kafka-consumer-lag-001
sparkforge-aws lab plan kafka-consumer-lag-001 --backend compose
sparkforge-aws lab run kafka-consumer-lag-001
sparkforge-aws lab inspect .sparkforge_aws/lab/runs/<run-id>
sparkforge-aws lab analyze .sparkforge_aws/lab/runs/<run-id>
sparkforge-aws lab compare <run-a> <run-b>
sparkforge-aws lab promote-fixture <run> fixtures/lab/<id> --reviewed
sparkforge-aws lab reproduce <run>/receipt.json
sparkforge-aws lab up --profile streaming
sparkforge-aws lab down --project forge-lab
sparkforge-aws lab shell --project forge-lab --service kafka
sparkforge-aws lab gc --project forge-lab
```

Every lifecycle command is plan-only by default. Local mutation requires both
`--execute --confirm`; AWS execution is a separate tier and remains refused by
the offline core.

## Fechamento da entrega

O fechamento da feature `FORGE_LAB_PRODUCT` foi registrado em
`docs/sdd/FORGE_LAB_PRODUCT/ship.md`. A verificação offline final retornou
`valid: true`, 11 componentes do registry, 20 cenários Golden e 240 ações
compiladas. A suíte final do repositório coletou 14301 testes e terminou com
14287 passados e 14 ignorados, depois da repetição dos lotes afetados por
guardas documentais.

Isso prova a integridade dos contratos e planos locais; não prova que imagens
Docker estão disponíveis no host, que um cenário L1 foi executado ou que uma
integração AWS foi validada. Sem transcript do host, `provider_tokens` continua
`unresolved_without_host_transcript`.

## Run layout and result classes

Runs live under `.sparkforge_aws/lab/runs/<run-id>/` and contain `run.json`,
`scenario.yaml`, `environment.json`, `versions.json`, `topology.json`,
`input/`, `logs/`, `metrics/`, `spark/`, `kafka/`, `flink/`, `iceberg/`,
`cdc/`, `facts/`, `findings/`, `receipt.json` and assertions. Result classes
are `PASS`, `FAIL`, `UNRESOLVED`, `INFRA_FAILURE` and `INVALID_SCENARIO`; a
container startup failure is not reported as a diagnosis failure.

## Safety and evidence boundary

Local Docker is a controlled L1 environment, not Glue, EMR, MSK, Kinesis or
Lake Formation. LocalStack/Moto-style service contracts are L2 only. L3 needs
explicit budget, TTL, region, prefix and tags, plus a cost receipt and cleanup
policy. No privileged container, host network, root mount, Docker socket or real
AWS credentials is allowed by the product contract.

The Lab proves only the declared scenario and runtime. It does not prove
production capacity, absolute latency, cloud pricing, AWS IAM semantics or
cross-version compatibility until those are captured in a receipt with runtime
versions and source evidence.
