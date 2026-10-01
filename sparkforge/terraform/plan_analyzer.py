"""Terraform Plan Risk Scanner and Action Classifier."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ResourceChangeFinding:
    address: str
    resource_type: str
    action: str  # create, update, delete, replace
    risk_level: str  # safe, review, high_risk, block
    reasons: list[str] = field(default_factory=list)


@dataclass
class TerraformPlanReport:
    total_creates: int
    total_updates: int
    total_deletes: int
    total_replaces: int
    overall_risk: str  # SAFE, REVIEW, HIGH_RISK, BLOCK
    findings: list[ResourceChangeFinding] = field(default_factory=list)
    has_data_loss_risk: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TerraformPlanAnalyzer:
    """Parses `terraform show -json tfplan` outputs to evaluate destruction,
    replacement, and IAM risk."""

    STATEFUL_RESOURCES = frozenset(
        {
            "aws_s3_bucket",
            "aws_dynamodb_table",
            "aws_msk_cluster",
            "aws_neptune_cluster",
            "aws_glue_catalog_database",
            "aws_glue_catalog_table",
            "aws_rds_cluster",
            "aws_redshift_cluster",
        }
    )

    def analyze_plan_json(self, plan_data: dict[str, Any]) -> TerraformPlanReport:
        creates = 0
        updates = 0
        deletes = 0
        replaces = 0
        findings: list[ResourceChangeFinding] = []
        has_data_loss = False

        resource_changes = plan_data.get("resource_changes", [])

        for rc in resource_changes:
            address = rc.get("address", "")
            rtype = rc.get("type", "")
            change = rc.get("change", {})
            actions = change.get("actions", [])

            action_name = "no-op"
            risk_level = "safe"
            reasons = []

            if actions == ["create"]:
                creates += 1
                action_name = "create"
            elif actions == ["update"]:
                updates += 1
                action_name = "update"
                risk_level = "review"
            elif actions == ["delete"]:
                deletes += 1
                action_name = "delete"
                if rtype in self.STATEFUL_RESOURCES:
                    risk_level = "block"
                    has_data_loss = True
                    reasons.append(
                        f"Destruction of stateful resource {rtype} will cause permanent data loss."
                    )
                else:
                    risk_level = "high_risk"
                    reasons.append(f"Resource deletion: {address}")
            elif "create" in actions and "delete" in actions:
                replaces += 1
                action_name = "replace"
                if rtype in self.STATEFUL_RESOURCES:
                    risk_level = "block"
                    has_data_loss = True
                    reasons.append(
                        f"Replacement (destroy + recreate) of stateful resource {rtype}."
                    )
                else:
                    risk_level = "high_risk"
                    reasons.append(f"Resource replacement: {address}")

            # Check IAM wildcard widening
            if "iam" in rtype:
                after_data = change.get("after", {}) or {}
                policy_doc = json.dumps(after_data)
                if '"Action": "*"' in policy_doc or '"Resource": "*"' in policy_doc:
                    risk_level = "block"
                    reasons.append("Unrestricted wildcard ('*') found in IAM policy.")

            if action_name != "no-op":
                findings.append(
                    ResourceChangeFinding(
                        address=address,
                        resource_type=rtype,
                        action=action_name,
                        risk_level=risk_level,
                        reasons=reasons,
                    )
                )

        overall = "SAFE"
        if any(f.risk_level == "block" for f in findings):
            overall = "BLOCK"
        elif any(f.risk_level == "high_risk" for f in findings):
            overall = "HIGH_RISK"
        elif any(f.risk_level == "review" for f in findings):
            overall = "REVIEW"

        return TerraformPlanReport(
            total_creates=creates,
            total_updates=updates,
            total_deletes=deletes,
            total_replaces=replaces,
            overall_risk=overall,
            findings=findings,
            has_data_loss_risk=has_data_loss,
        )
