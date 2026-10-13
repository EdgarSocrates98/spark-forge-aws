---
applyTo: "**/*.{py,sql}"
---

For Apache Iceberg:
- Confirm the AWS Glue and Iceberg versions.
- Consider data files, delete files, manifests, snapshots and metadata independently.
- Validate partition spec, sort order and query filters.
- Treat expire snapshots and remove orphan files as potentially destructive.
- Require retention, concurrency analysis, validation and rollback.
