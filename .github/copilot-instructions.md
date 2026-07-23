# SparkForge AWS Copilot Instructions

This repository contains PySpark jobs designed for AWS Glue, Amazon S3, Parquet and Apache Iceberg.

Always:
- detect Glue/Spark/Python/Iceberg versions;
- inspect execution plans and metrics before tuning;
- prioritize reducing scans, cardinality and shuffle;
- prefer native Spark functions over Python UDFs;
- preserve correctness and validate outputs;
- include evidence, risks, trade-offs, benchmark and rollback;
- avoid collect, toPandas, coalesce(1), arbitrary repartition and unjustified cache;
- distinguish Parquet file layout from Iceberg metadata maintenance;
- do not propose destructive Iceberg maintenance without explicit retention and safety controls.
