# Streaming Reliability

Use for Kinesis, Kafka/MSK, Flink and Structured Streaming without internet. Separate observed lag, throughput, shards, watermark, checkpoint, duplicates, replay, backpressure and state.

## Checklist
1. Identify source, partitioning, consumer group, checkpoint and retention.
2. Measure lag per partition, input, output, errors, retries and state size.
3. Verify sink idempotency, dead letter and checkpoint loss behavior.
4. Never promise exactly-once without confirming engine, sink and commit.

## Sources
- https://docs.aws.amazon.com/streams/latest/dev/introduction.html
- https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
- https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/state/
