#!/usr/bin/env python3
"""Reusable skew profiler for a Spark DataFrame."""
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def profile_key_skew(df: DataFrame, keys: list[str], top_n: int = 20) -> dict:
    if not keys:
        raise ValueError("keys must not be empty")

    counts = df.groupBy(*keys).count()
    total = df.count()
    distinct = counts.count()

    stats_row = counts.agg(
        F.max("count").alias("max_rows_per_key"),
        F.expr("percentile_approx(count, 0.5)").alias("p50"),
        F.expr("percentile_approx(count, 0.95)").alias("p95"),
        F.expr("percentile_approx(count, 0.99)").alias("p99"),
        F.avg("count").alias("mean"),
        F.stddev_pop("count").alias("stddev"),
    ).first()

    top_rows = counts.orderBy(F.desc("count")).limit(top_n).collect()
    top = [row.asDict(recursive=True) for row in top_rows]
    p50 = stats_row["p50"] or 0
    mean = stats_row["mean"] or 0

    return {
        "total_rows": total,
        "distinct_keys": distinct,
        "max_rows_per_key": stats_row["max_rows_per_key"],
        "p50_rows_per_key": p50,
        "p95_rows_per_key": stats_row["p95"],
        "p99_rows_per_key": stats_row["p99"],
        "max_to_median_ratio": (stats_row["max_rows_per_key"] / p50) if p50 else None,
        "coefficient_of_variation": (stats_row["stddev"] / mean) if mean else None,
        "top_keys": top,
    }
