"""AWS Glue 4.0 -> 5.1 Migration Intelligence and Assessment Engine."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class MigrationFinding:
    category: str  # spark, python, java, s3_filesystem, lakeformation, iceberg, parquet
    severity: str  # critical, high, medium, low
    title: str
    description: str
    action_required: str


@dataclass
class GlueMigrationAssessment:
    source_runtime: str
    target_runtime: str
    readiness_score: int  # 0 - 100
    decision: str  # GO, CONDITIONAL_GO, NO_GO
    breaking_changes: list[MigrationFinding] = field(default_factory=list)
    required_changes: list[MigrationFinding] = field(default_factory=list)
    recommended_changes: list[MigrationFinding] = field(default_factory=list)
    s3_filesystem_status: str = "ok"
    lakeformation_status: str = "ok"
    iceberg_status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class GlueMigrationAnalyzer:
    """Analyzes PySpark scripts, requirements, and job configurations for Glue 4.0 -> 5.1 migration."""

    def analyze_script(
        self,
        script_content: str,
        source_runtime: str = "4.0",
        target_runtime: str = "5.1",
    ) -> GlueMigrationAssessment:
        breaking: list[MigrationFinding] = []
        required: list[MigrationFinding] = []
        recommended: list[MigrationFinding] = []

        # 1. S3A vs EMRFS filesystem check
        if "fs.s3a." in script_content or "org.apache.hadoop.fs.s3a.S3AFileSystem" in script_content:
            breaking.append(
                MigrationFinding(
                    category="s3_filesystem",
                    severity="high",
                    title="Direct S3A filesystem configuration detected",
                    description="Glue 5.1 updates AWS SDK and Hadoop filesystem connectors. Explicit S3A overrides may conflict with Glue 5.1 native S3 client.",
                    action_required="Migrate `fs.s3a.*` configurations to native Glue/Spark `s3://` connector.",
                )
            )

        # 2. Python runtime check
        if "python_version" in script_content and "3.10" in script_content and target_runtime == "5.1":
            required.append(
                MigrationFinding(
                    category="python",
                    severity="medium",
                    title="Python 3.10 runtime declared",
                    description="Glue 5.1 uses Python 3.11+. Pinning Python 3.10 is not supported in Glue 5.1.",
                    action_required="Upgrade dependencies to be compatible with Python 3.11.",
                )
            )

        # 3. Iceberg Catalog check
        if "org.apache.iceberg.spark.SparkCatalog" in script_content:
            if "spark.sql.catalog.glue_catalog.warehouse" not in script_content:
                required.append(
                    MigrationFinding(
                        category="iceberg",
                        severity="medium",
                        title="Iceberg SparkCatalog missing warehouse path",
                        description="Glue 5.1 Iceberg integration requires explicit warehouse configuration.",
                        action_required="Set `spark.sql.catalog.<name>.warehouse` in job arguments.",
                    )
                )

        # 4. DynamicFrame / GlueContext
        if "GlueContext" in script_content and "create_dynamic_frame" in script_content:
            recommended.append(
                MigrationFinding(
                    category="spark",
                    severity="low",
                    title="DynamicFrame used instead of native Spark DataFrame",
                    description="In Glue 5.1, Spark SQL DataFrames leverage Spark 3.5 Catalyst optimizations more effectively than legacy DynamicFrames.",
                    action_required="Consider converting read/write operations to native DataFrame where possible.",
                )
            )

        # Calculate readiness score
        score = 100
        for b in breaking:
            score -= 30 if b.severity == "critical" else 20
        for r in required:
            score -= 10
        score = max(0, min(100, score))

        decision = "GO"
        if score < 60 or any(b.severity == "critical" for b in breaking):
            decision = "NO_GO"
        elif score < 90 or breaking:
            decision = "CONDITIONAL_GO"

        return GlueMigrationAssessment(
            source_runtime=source_runtime,
            target_runtime=target_runtime,
            readiness_score=score,
            decision=decision,
            breaking_changes=breaking,
            required_changes=required,
            recommended_changes=recommended,
            s3_filesystem_status="warning" if any(b.category == "s3_filesystem" for b in breaking) else "ok",
        )
