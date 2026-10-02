# Scenario DSL

`golden.yaml` is the independent Golden 20 seed corpus. It is declarative:
dataset, workload, topology, fault, observations, expected facts/findings,
forbidden findings, unresolved expectations and experiment plan are data.

The compiler emits only allowlisted actions. It never turns a scenario into an
arbitrary shell script. Heavy L1 runs belong under `.sparkforge/lab/runs/` and
curated fixtures require human review plus a valid receipt before promotion.
