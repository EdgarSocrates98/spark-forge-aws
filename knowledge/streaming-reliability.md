# Streaming Reliability

Use this page as offline operating knowledge for streaming systems. Keep
Structured Streaming, Kafka/MSK, Kinesis, Flink, CDC and sink semantics
separate: the same word (lag, checkpoint, watermark, exactly-once) can refer to
different evidence in each engine.

## First evidence wave: Structured Streaming

SparkForge now treats two artifacts as first-class evidence:

* **Source AST** describes what the code declares: source, sink, checkpoint,
  trigger, output mode, watermark, stateful operation, join, deduplication,
  `foreachBatch`, query and the module sentinel.
* **`StreamingQueryProgress` JSON/JSONL** describes what a run observed:
  batch duration, input/output rates and rows, source offsets, sink rows,
  event-time values and state-operator measurements. A series fact is emitted
  only with at least two valid observations and at least one complete numeric
  series. It compactly preserves observed timestamp span, batch duration,
  total state memory and watermark values when their series is complete.

Static source facts are not runtime measurements. A progress series is not a
backlog measurement unless the transport backlog is also collected. Boolean
interpretations live in `attrs`; numeric quantities and their units live in
`measures`. Missing or malformed observations become
`streaming.progress.unresolved`, never zero.

Use:

```text
sparkforge-aws analyze streaming --artifact source --path <job.py-or-dir>
sparkforge-aws analyze streaming --artifact progress --path <progress.jsonl-or-dir>
```

The MCP equivalent is `sparkforge_analyze_streaming` with the same `path`,
`artifact`, `kind`, `limit`, `cursor` and `detail_level` contract. The first
rules are deliberately evidence-gated:

* `SF-STREAM-001`: static query without a declared checkpoint, requiring an
  observed runtime and confirmation of effective external configuration.
* `SF-STREAM-002`: every observed point in a sufficient series has processed
  rate below input rate; it does not identify the bottleneck.
* `SF-STREAM-003`: state rows grew between first and last observed point; it
  does not prove a leak or prescribe a watermark.
* `SF-STREAM-013`: watermark values stayed equal across a valid observed
  series; it does not prove missing input, clock failure or freshness breach.
* `SF-STREAM-014`: summed `memoryUsedBytes` across state operators grew between
  first and last valid point; it does not prove a leak or justify scaling.

These rules request a baseline. They do not promise throughput, cost savings,
exactly-once delivery or a universal version boundary. Correlate source,
transport backlog, trigger duration, state store, sink commit, runtime and
functional result before changing one primary variable.

## Field checklist

1. Identify source format, partitions/shards, consumer group, retention,
   checkpoint location and query identity.
2. Capture runtime/version evidence before judging API or service capability.
3. Measure input, processed and output rows with timestamps, batch IDs and
   units; preserve source offsets and sink commit evidence.
4. Correlate watermark, event-time distribution, late data, state rows and the
   compact series measures `observed_span_seconds`, batch duration and state
   memory. `watermark_stalled` and `state_memory_growth_observed` are symptoms,
   not causes.
5. Verify sink idempotency, replay, dead-letter behavior and checkpoint loss
   handling before claiming correctness.
6. Validate count, schema, business keys and control aggregates after every
   optimization or replay.
7. Never promise exactly-once without confirming engine, source, sink and
   commit protocol for the detected runtime.

## Scope and unresolved work

Kafka/MSK, Kinesis e Flink/Managed Flink já possuem ondas de evidência
implementadas: dumps offline, facts específicos, unresolved e, quando a janela
é declarada, collectors read-only bounded e composição temporal. Consulte
[`transport-diagnostics.md`](transport-diagnostics.md) para transporte e
[`flink-streaming.md`](flink-streaming.md) para os dois namespaces Flink.

Isso não transforma um snapshot em série longa nem em estado live. Connect REST,
Kafka Streams runtime, OpenLineage live, replay, benchmark, validação funcional,
runtime regional/efetivo, segurança completa e atribuição de FinOps continuam
dependendo do artefato, endpoint, credencial ou workload correspondente. CDC,
DMS/Debezium, Schema Registry, Iceberg streaming e serving também permanecem
parciais e devem ser roteados para seus analyzers/skills específicos; a presença
do domínio nesta página nunca prova que o extrator ou collector foi executado.

## Official sources

* https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
* https://spark.apache.org/docs/latest/api/python/reference/pyspark.ss/api/pyspark.sql.streaming.StreamingQuery.lastProgress.html
* https://spark.apache.org/docs/latest/api/python/_modules/pyspark/sql/streaming/listener.html
* https://docs.aws.amazon.com/glue/latest/dg/add-job-streaming.html
* https://docs.aws.amazon.com/en_en/glue/latest/dg/edit-jobs-source-streaming.html
* https://docs.aws.amazon.com/streams/latest/dev/introduction.html
* https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
* https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/state/
