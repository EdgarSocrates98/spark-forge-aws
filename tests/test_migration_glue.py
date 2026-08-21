"""Tests for AWS Glue 4.0 -> 5.1 Migration Intelligence."""
import pytest
from sparkforge.migration.glue.analyzer import GlueMigrationAnalyzer


def test_glue_migration_s3a_and_python_detection():
    analyzer = GlueMigrationAnalyzer()
    script = """
    import sys
    from awsglue.context import GlueContext
    from pyspark.context import SparkContext

    sc = SparkContext()
    sc._jsc.hadoopConfiguration().set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    python_version = "3.10"
    """
    assessment = analyzer.analyze_script(script, source_runtime="4.0", target_runtime="5.1")
    assert assessment.decision in ("CONDITIONAL_GO", "NO_GO")
    assert assessment.readiness_score < 100
    assert assessment.s3_filesystem_status == "warning"
    assert any(b.category == "s3_filesystem" for b in assessment.breaking_changes)
    assert any(r.category == "python" for r in assessment.required_changes)


def test_glue_migration_clean_script():
    analyzer = GlueMigrationAnalyzer()
    script = """
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("clean_glue5").getOrCreate()
    df = spark.read.parquet("s3://bucket/data/")
    df.write.mode("append").parquet("s3://bucket/output/")
    """
    assessment = analyzer.analyze_script(script, source_runtime="4.0", target_runtime="5.1")
    assert assessment.decision == "GO"
    assert assessment.readiness_score >= 90
    assert len(assessment.breaking_changes) == 0
