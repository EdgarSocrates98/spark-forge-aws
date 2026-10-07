# Data Contracts and Schema Evolution

Base for contracts, Avro, Protobuf, JSON Schema and Glue Schema Registry. Classify changes as compatible, incompatible or uncertain.

## Procedure
1. Capture old and new schemas, version, producer and consumers.
2. Compare fields, types, required, defaults, enum and semantics.
3. Verify contract tests and migration window.
4. Produce impact and rollback.

## Sources
- https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html
- https://avro.apache.org/docs/current/specification/
- https://json-schema.org/specification
