# Scenario DSL

`golden.yaml` is the independent Golden 20 seed corpus. It is declarative:
dataset, workload, topology, fault, observations, expected facts/findings,
forbidden findings, unresolved expectations and experiment plan are data.

The compiler emits only allowlisted actions. It never turns a scenario into an
arbitrary shell script. `sparkforge-aws lab verify` checks the registry, all 20
Golden scenarios, schemas and compiled action plans offline. Heavy L1 runs
belong under `.sparkforge_aws/lab/runs/` and curated fixtures require human review
plus a valid receipt before promotion.
