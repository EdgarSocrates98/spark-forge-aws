from sparkforge.facts.pyspark_ast import extract_source


def test_extract_structured_streaming_source_emits_anchored_facts():
    source = '''
from pyspark.sql import functions as F

events = (
    spark.readStream.format("kafka")
    .option("subscribe", "events")
    .load()
    .withWatermark("event_time", "10 minutes")
    .dropDuplicates(["event_id"])
)
other = spark.readStream.format("rate").load()
joined = events.join(other, "event_id")
query = (
    joined.groupBy(F.window("event_time", "5 minutes"), "event_id")
    .count()
    .writeStream.format("iceberg")
    .outputMode("append")
    .option("checkpointLocation", "s3://bucket/checkpoints/events")
    .trigger(processingTime="30 seconds")
    .foreachBatch(write_batch)
    .start()
)
'''

    facts = extract_source(source, "fixtures/streaming/source.py")
    streaming = [fact for fact in facts if fact.kind.startswith("streaming.")]
    kinds = {fact.kind for fact in streaming}

    assert {
        "streaming.source",
        "streaming.sink",
        "streaming.checkpoint",
        "streaming.trigger",
        "streaming.output_mode",
        "streaming.watermark",
        "streaming.stateful_operation",
        "streaming.join",
        "streaming.dedup",
        "streaming.foreach_batch",
        "streaming.query",
        "streaming.module_analyzed",
    } <= kinds
    assert streaming
    assert all(fact.subject["file"] == "fixtures/streaming/source.py" for fact in streaming)
    assert all(fact.subject["line"] > 0 for fact in streaming if fact.kind != "streaming.module_analyzed")
    assert all(fact.provenance["extractor"] == "pyspark_ast@0.1.0" for fact in streaming)

    batch = extract_source(
        'df = spark.read.format("parquet").load("s3://bucket/input")\n'
        'df.write.format("parquet").save("s3://bucket/output")\n',
        "fixtures/streaming/batch.py",
    )
    assert not [fact for fact in batch if fact.kind.startswith("streaming.")]
