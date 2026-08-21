<!-- GENERATED FROM CANONICAL SOURCE — DO NOT EDIT DIRECTLY -->
# Migration Safety Rule — SparkForge AWS

1. Every Glue 4.0 ➔ 5.1 migration must evaluate Spark, Python, Java/JAR, S3 filesystem, Iceberg, and Lake Formation compatibility.
2. Functional validation (row count, schema, key aggregates) is required before declaring migration readiness.
3. Check for S3A / EMRFS filesystem assumption breaks in Glue 5.1.
4. Establish baseline performance benchmarks before applying runtime upgrades.
