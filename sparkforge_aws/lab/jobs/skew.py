"""Produce a real Spark event log and partition-skew observation for LAB-002.

The job is intentionally self-contained so the Compose lab does not mount the
host filesystem or import project code inside the Spark container.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from pyspark.sql import SparkSession


def main() -> int:
    args = _parse_args()
    Path(args.event_dir).mkdir(parents=True, exist_ok=True)
    spark = (
        SparkSession.builder.appName("ForgeLab-LAB-002")
        .master("local[2]")
        .config("spark.eventLog.enabled", "true")
        .config("spark.eventLog.compress", "false")
        .config("spark.eventLog.dir", f"file://{args.event_dir}")
        .config("spark.sql.shuffle.partitions", str(args.partitions))
        .getOrCreate()
    )
    try:
        rows = [
            (0 if index < int(args.records * args.skew) else index % args.cardinality, index)
            for index in range(args.records)
        ]
        frame = spark.createDataFrame(rows, ["entity_id", "event_id"])
        repartitioned = frame.repartition(args.partitions, "entity_id")
        counts = repartitioned.rdd.mapPartitions(_measure_partition).collect()
        # Force a real Spark action after the repartition so the event log has
        # completed stages and task metrics for the Forge event-log analyzer.
        repartitioned.groupBy("entity_id").count().collect()
        ordered = sorted(int(value) for value in counts)
        p50 = ordered[len(ordered) // 2] if ordered else 0
        skew_ratio = (max(ordered) / p50) if p50 else None
        payload = {
            "facts": [
                {
                    "kind": "spark.partition.skew",
                    "subject": {
                        "type": "stage",
                        "stage_id": 0,
                        "symbol": "ForgeLab-LAB-002",
                    },
                    "measures": {
                        "max_partition_records": max(ordered) if ordered else 0,
                        "p50_partition_records": p50,
                        "skew_ratio": skew_ratio or 0,
                    },
                    "attrs": {
                        "partition_counts": ordered,
                    },
                    "provenance": {"artifact": "spark-local-observation"},
                }
            ],
            "partition_counts": ordered,
            "records": args.records,
            "seed": args.seed,
        }
        Path(args.output).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    finally:
        spark.stop()
    return 0


def _measure_partition(rows):
    values = list(rows)
    if len(values) > 100:
        time.sleep(1.0)
    yield len(values)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--event-dir", required=True)
    parser.add_argument("--records", type=int, required=True)
    parser.add_argument("--cardinality", type=int, required=True)
    parser.add_argument("--skew", type=float, required=True)
    parser.add_argument("--partitions", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
