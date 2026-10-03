from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.facts.streaming import extract_streaming_progress_path


def _progress(batch_id: int, input_rate: float, processed_rate: float, state_rows: int) -> dict:
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "runId": "00000000-0000-0000-0000-000000000002",
        "name": "orders",
        "timestamp": f"2026-10-01T00:00:0{batch_id}Z",
        "batchId": batch_id,
        "batchDuration": 1000,
        "durationMs": {"addBatch": 500, "commitOffsets": 100},
        "eventTime": {"watermark": f"2026-10-01T00:00:0{batch_id}Z"},
        "stateOperators": [
            {
                "operatorName": "stateStoreSave",
                "numRowsTotal": state_rows,
                "numRowsUpdated": state_rows,
                "memoryUsedBytes": 2048 + batch_id,
            }
        ],
        "sources": [
            {
                "description": "KafkaV2[Subscribe[orders]]",
                "startOffset": "{0: 1}",
                "endOffset": "{0: 2}",
                "latestOffset": "{0: 2}",
                "numInputRows": 100 + batch_id,
                "inputRowsPerSecond": input_rate,
                "processedRowsPerSecond": processed_rate,
            }
        ],
        "sink": {
            "description": "org.apache.spark.sql.execution.streaming.SinkProgress",
            "numOutputRows": 100 + batch_id,
        },
        "numInputRows": 100 + batch_id,
        "inputRowsPerSecond": input_rate,
        "processedRowsPerSecond": processed_rate,
        "observedMetrics": {},
    }


def test_extract_streaming_progress_emits_batch_source_sink_and_state_facts(tmp_path):
    path = tmp_path / "progress.jsonl"
    path.write_text(
        "\n".join(
            [
                __import__("json").dumps(_progress(0, 100.0, 80.0, 10)),
                __import__("json").dumps(_progress(1, 110.0, 90.0, 20)),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    facts = extract_streaming_progress_path(path, repo_root=tmp_path)
    kinds = {fact.kind for fact in facts}

    assert {
        "streaming.progress.batch",
        "streaming.progress.source",
        "streaming.progress.sink",
        "streaming.progress.event_time",
        "streaming.progress.state_operator",
        "streaming.progress.series",
        "streaming.progress.analyzed",
    } <= kinds
    batches = [fact for fact in facts if fact.kind == "streaming.progress.batch"]
    assert [fact.measures["batch_id"] for fact in batches] == [0, 1]
    assert [fact.measures["observed_index"] for fact in batches] == [0, 1]
    assert all(fact.measures["duration_ms_addBatch"] == 500 for fact in batches)
    assert all(fact.provenance["artifact_sha256"] for fact in facts)


def test_insufficient_progress_is_unresolved_not_a_trend(tmp_path):
    path = tmp_path / "single.jsonl"
    path.write_text(__import__("json").dumps(_progress(0, 100.0, 80.0, 10)) + "\n", encoding="utf-8")

    facts = extract_streaming_progress_path(path, repo_root=tmp_path)
    unresolved = [fact for fact in facts if fact.kind == "streaming.progress.unresolved"]

    assert unresolved
    assert unresolved[0].attrs["reason"] == "insufficient_series"
    assert unresolved[0].attrs["observed_observations"] == 1
    assert not [fact for fact in facts if fact.kind == "streaming.progress.series"]


def test_streaming_extraction_is_deterministic_and_batch_safe(tmp_path):
    path = tmp_path / "progress.jsonl"
    path.write_text(__import__("json").dumps(_progress(0, 100.0, 80.0, 10)) + "\n", encoding="utf-8")
    first = [fact.to_dict() for fact in extract_streaming_progress_path(path, repo_root=tmp_path)]
    second = [fact.to_dict() for fact in extract_streaming_progress_path(path, repo_root=tmp_path)]
    assert first == second

    batch = extract_source(
        'df = spark.read.format("parquet").load("s3://bucket/input")\n'
        'df.write.format("parquet").save("s3://bucket/output")\n',
        "fixtures/streaming/batch.py",
    )
    assert not [fact for fact in batch if fact.kind.startswith("streaming.")]


def test_progress_series_summarizes_temporal_state_and_watermark(tmp_path):
    first = _progress(0, 100.0, 100.0, 10)
    second = _progress(1, 100.0, 100.0, 10)
    first["batchDuration"] = 1000
    second["batchDuration"] = 1400
    first["eventTime"]["watermark"] = "2026-10-01T00:00:00Z"
    second["eventTime"]["watermark"] = "2026-10-01T00:00:00Z"
    first["stateOperators"][0]["memoryUsedBytes"] = 2048
    second["stateOperators"][0]["memoryUsedBytes"] = 4096
    path = tmp_path / "progress.jsonl"
    path.write_text(
        "\n".join(__import__("json").dumps(item) for item in (first, second)) + "\n",
        encoding="utf-8",
    )

    facts = extract_streaming_progress_path(path, repo_root=tmp_path)
    series = next(fact for fact in facts if fact.kind == "streaming.progress.series")

    assert series.measures["observed_span_seconds"] == 1.0
    assert series.measures["batch_duration_ms_first"] == 1000
    assert series.measures["batch_duration_ms_last"] == 1400
    assert series.measures["batch_duration_ms_max"] == 1400
    assert series.measures["state_memory_used_bytes_first"] == 2048
    assert series.measures["state_memory_used_bytes_last"] == 4096
    assert series.attrs["watermark_stalled"] is True
    assert series.attrs["state_memory_growth_observed"] is True


def test_progress_series_unresolved_for_invalid_temporal_measurement(tmp_path):
    first = _progress(0, 100.0, 100.0, 10)
    second = _progress(1, 100.0, 100.0, 10)
    second["eventTime"]["watermark"] = "not-a-timestamp"
    path = tmp_path / "progress.jsonl"
    path.write_text(
        "\n".join(__import__("json").dumps(item) for item in (first, second)) + "\n",
        encoding="utf-8",
    )

    facts = extract_streaming_progress_path(path, repo_root=tmp_path)
    unresolved = [fact for fact in facts if fact.kind == "streaming.progress.unresolved"]
    series = next(fact for fact in facts if fact.kind == "streaming.progress.series")

    assert any(fact.attrs["reason"] == "invalid_watermark_series" for fact in unresolved)
    assert "watermark_stalled" not in series.attrs


def test_progress_derives_freshness_only_from_event_time_max(tmp_path):
    first = _progress(0, 100.0, 100.0, 10)
    second = _progress(1, 100.0, 100.0, 10)
    first["timestamp"] = "2026-10-01T00:00:05Z"
    second["timestamp"] = "2026-10-01T00:05:20Z"
    first["eventTime"]["max"] = "2026-10-01T00:00:00Z"
    second["eventTime"]["max"] = "2026-10-01T00:05:00Z"
    path = tmp_path / "progress.jsonl"
    path.write_text(
        "\n".join(__import__("json").dumps(item) for item in (first, second)) + "\n",
        encoding="utf-8",
    )

    facts = extract_streaming_progress_path(path, repo_root=tmp_path)
    batches = [fact for fact in facts if fact.kind == "streaming.progress.batch"]
    assert [fact.measures["freshness_ms"] for fact in batches] == [5000.0, 20000.0]
    assert not [
        fact
        for fact in facts
        if fact.kind == "streaming.progress.unresolved"
        and fact.attrs["reason"] == "invalid_freshness_measurement"
    ]

    second["eventTime"]["max"] = "not-a-timestamp"
    path.write_text(
        "\n".join(__import__("json").dumps(item) for item in (first, second)) + "\n",
        encoding="utf-8",
    )
    invalid_facts = extract_streaming_progress_path(path, repo_root=tmp_path)
    assert any(
        fact.attrs["reason"] == "invalid_freshness_measurement"
        for fact in invalid_facts
        if fact.kind == "streaming.progress.unresolved"
    )
    invalid_batches = [fact for fact in invalid_facts if fact.kind == "streaming.progress.batch"]
    assert "freshness_ms" not in invalid_batches[1].measures


def test_progress_preserves_explicit_end_to_end_latency(tmp_path):
    first = _progress(0, 100.0, 100.0, 10)
    second = _progress(1, 100.0, 100.0, 10)
    first["endToEndLatencyMs"] = 120.0
    second["endToEndLatencyMs"] = 180.0
    path = tmp_path / "progress.jsonl"
    path.write_text(
        "\n".join(__import__("json").dumps(item) for item in (first, second)) + "\n",
        encoding="utf-8",
    )

    facts = extract_streaming_progress_path(path, repo_root=tmp_path)
    batches = [fact for fact in facts if fact.kind == "streaming.progress.batch"]
    assert [fact.measures["end_to_end_latency_ms"] for fact in batches] == [120.0, 180.0]


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
