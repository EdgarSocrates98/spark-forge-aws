# Streaming pipeline diagnostics

SparkForge composes evidence from CDC, transport, processor and sink only when
the operator declares their identity. The pipeline contract is a join contract,
not topology discovery and not a runtime health check.

## Contract

```json
{
  "schema_version": 1,
  "pipeline_id": "orders",
  "nodes": [
    {"id": "cdc", "selector": {"kind": "cdc.event", "attrs": {"topic": "orders"}}}
  ],
  "edges": [{"id": "cdc-to-transport", "from": "cdc", "to": "transport"}]
}
```

Each selector compares `Fact.kind` and every declared scalar attribute by exact
equality. A node is `verified` only with one match. Zero matches produce
`selector_not_found`; multiple matches produce `selector_ambiguous`. No
substring, name similarity, array matching, source order or co-existence is
accepted as identity.

An edge is `verified` only when both endpoint nodes are verified. The composed
facts preserve `source_fact_ids`, provenance and `causal_inference: false`.
`streaming.pipeline.unresolved` names the missing contract evidence; it does
not claim that the real system lacks the component.

Run offline:

```text
sparkforge-aws analyze streaming-composition \
  --facts cdc-facts.json --facts kafka-facts.json --facts flink-facts.json \
  --facts iceberg-facts.json --mode pipeline \
  --pipeline-path orders-pipeline.json
```

The same contract is available through
`sparkforge_analyze_streaming_composition` with `pipeline_path`. CLI and MCP
call the same core and preserve `detail_level`, pagination and fact ids.

## What this proves

The result proves only that declared nodes and edges were or were not matched
against the supplied facts. It can support the next evidence request across
CDC, Kafka/MSK/Kinesis, Flink/Spark/Glue and Iceberg/serving. It does not prove
end-to-end latency, throughput, availability, backlog, exactly-once delivery,
health, causal dependency, cost or functional equivalence.

## Operating loop

1. Extract each artifact independently and preserve its runtime/provenance.
2. Write a versioned contract with stable ids and exact scalar selectors.
3. Compose with `mode=pipeline` and inspect every unresolved node/edge.
4. Collect the missing artifact or disambiguating identity; do not relax a
   selector merely to remove unresolved.
5. Correlate timestamps, commits, SLOs, cost and functional validation only
   after the topology evidence is complete for the question.

## Sources and limits

Structured Streaming documents query progress and source/sink concepts, but
does not supply cross-engine identity. OpenLineage's object model is a useful
lineage vocabulary, not evidence that a declared edge exists in a particular
run. Live collectors, endpoint discovery, replay and causal inference remain
outside this offline compositor.

- https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
- https://openlineage.io/docs/spec/object-model
