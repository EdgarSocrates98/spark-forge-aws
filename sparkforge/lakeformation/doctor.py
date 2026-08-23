"""Lake Formation Cross-Account Doctor and Access Model Advisor."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class CrossAccountHealthReport:
    health_score: int  # 0 - 100
    pass_items: list[str] = field(default_factory=list)
    fail_items: list[str] = field(default_factory=list)
    warn_items: list[str] = field(default_factory=list)
    unresolved_items: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LakeFormationDoctor:
    """Diagnoses cross-account permissions and recommends FTA vs FGAC models."""

    def diagnose_cross_account(self, config_dump: dict[str, Any]) -> CrossAccountHealthReport:
        passes = []
        fails = []
        warns = []
        unresolved = []
        recs = []

        ram_status = config_dump.get("ram_share_status", "")
        if ram_status == "ACCEPTED":
            passes.append("AWS RAM resource share is ACCEPTED")
        elif ram_status == "PENDING":
            fails.append("AWS RAM resource share is PENDING acceptance")
            recs.append("Accept RAM share in AWS RAM console or CLI.")
        else:
            unresolved.append("RAM resource share status unknown")

        resource_link = config_dump.get("resource_link_exists", False)
        if resource_link:
            passes.append("Glue Resource Link exists in consumer account")
        else:
            fails.append("Glue Resource Link missing in consumer account")
            recs.append("Create Resource Link in consumer Data Catalog pointing to shared database/table.")

        kms_shared = config_dump.get("kms_key_policy_includes_consumer", None)
        if kms_shared is True:
            passes.append("KMS Key Policy explicitly authorizes consumer role")
        elif kms_shared is False:
            warns.append("KMS Key Policy does not explicitly list consumer role ARN")
            recs.append("Add consumer account/role to KMS Key Policy.")
        else:
            unresolved.append("KMS key policy unavailable")

        score = 100 - (len(fails) * 35) - (len(warns) * 15)
        score = max(0, min(100, score))

        return CrossAccountHealthReport(
            health_score=score,
            pass_items=passes,
            fail_items=fails,
            warn_items=warns,
            unresolved_items=unresolved,
            recommendations=recs,
        )

    def recommend_access_model(
        self,
        has_row_filters: bool = False,
        has_column_filters: bool = False,
        is_bulk_etl: bool = True,
        is_native_spark: bool = True,
    ) -> dict[str, Any]:
        if has_row_filters or has_column_filters:
            return {
                "model": "FGAC",
                "title": "Fine-Grained Access Control Required",
                "reason": "Row/Column level security filters declared.",
                "overhead_estimate": "Moderate (Data filtering daemon active)",
                "glue_worker_recommendation": "Use Glue G.2X or higher with GlueContext.",
            }
        return {
            "model": "FTA",
            "title": "Full Table Access (FTA) Recommended",
            "reason": "No row/column filters required; bulk ETL leverages direct S3 vectorized reads.",
            "overhead_estimate": "Minimal (Zero filter proxy overhead)",
            "glue_worker_recommendation": "Standard G.1X / G.2X with native Spark DataFrames.",
        }
