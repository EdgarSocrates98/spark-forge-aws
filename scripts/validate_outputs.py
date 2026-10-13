#!/usr/bin/env python3
"""Logical comparison helpers for before/after Spark DataFrames."""
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def dataset_signature(df: DataFrame, key_columns: list[str] | None = None) -> dict:
    columns = sorted(df.columns)
    normalized = F.concat_ws(
        "||",
        *[F.coalesce(F.col(c).cast("string"), F.lit("<NULL>")) for c in columns]
    )
    row = df.agg(
        F.count("*").alias("row_count"),
        F.sum(F.xxhash64(normalized)).alias("hash_sum"),
        F.min(F.xxhash64(normalized)).alias("hash_min"),
        F.max(F.xxhash64(normalized)).alias("hash_max"),
    ).first()

    result = {
        "schema": df.schema.json(),
        "row_count": row["row_count"],
        "hash_sum": row["hash_sum"],
        "hash_min": row["hash_min"],
        "hash_max": row["hash_max"],
    }

    if key_columns:
        result["duplicate_key_groups"] = (
            df.groupBy(*key_columns).count().filter(F.col("count") > 1).count()
        )
    return result
