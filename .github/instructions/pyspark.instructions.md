---
applyTo: "**/*.py"
---

For PySpark code:
- Identify every action and shuffle boundary.
- Push filters and projections as early as semantically safe.
- Reduce columns before joins.
- Analyze key distribution before treating skew.
- Prefer Spark SQL native expressions.
- Do not add cache unless reuse and memory benefit are demonstrated.
- Do not hard-code shuffle partitions without workload evidence.
- Include data-correctness tests with performance changes.
