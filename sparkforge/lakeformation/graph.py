"""Lake Formation Deterministic Permission Graph Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class PermissionEdge:
    source_node: str
    target_node: str
    permission_type: str  # iam, lf_grant, ram_share, s3_bucket_policy, kms_decrypt
    status: str  # granted, missing, blocking, uncertain
    evidence: str = ""


@dataclass
class PermissionGraphAnalysis:
    principal_arn: str
    target_table_arn: str
    is_accessible: bool
    effective_path: list[str]
    missing_permissions: list[PermissionEdge] = field(default_factory=list)
    blocking_permissions: list[PermissionEdge] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class LakeFormationPermissionGraph:
    """Traces access path: Principal -> IAM -> LF -> Catalog -> Resource Link -> RAM -> S3 -> KMS."""

    def evaluate_access(
        self,
        principal_arn: str,
        target_table: str,
        grants: list[dict[str, Any]],
        ram_shares: list[dict[str, Any]],
        kms_keys: list[dict[str, Any]],
        is_cross_account: bool = False,
    ) -> PermissionGraphAnalysis:
        effective_path = [principal_arn]
        missing: list[PermissionEdge] = []
        blocking: list[PermissionEdge] = []
        recommendations: list[str] = []

        # Check Lake Formation Catalog/Table grant
        has_table_grant = any(
            g.get("table", "") == target_table and "SELECT" in g.get("permissions", [])
            for g in grants
        )

        if has_table_grant:
            effective_path.append("lakeformation:TableGrant")
        else:
            edge = PermissionEdge(
                source_node=principal_arn,
                target_node=f"lakeformation:{target_table}",
                permission_type="lf_grant",
                status="missing",
                evidence=f"No SELECT grant found on {target_table}",
            )
            missing.append(edge)
            recommendations.append(f"Grant SELECT permission on Lake Formation table {target_table}")

        # If cross-account, check RAM and Resource Link
        if is_cross_account:
            has_ram_share = any(r.get("status") == "ACCEPTED" for r in ram_shares)
            if has_ram_share:
                effective_path.append("ram:ResourceShare")
                effective_path.append("glue:ResourceLink")
            else:
                missing.append(
                    PermissionEdge(
                        source_node="ram:share",
                        target_node="consumer:account",
                        permission_type="ram_share",
                        status="missing",
                        evidence="RAM resource share not accepted in consumer account",
                    )
                )
                recommendations.append("Accept AWS RAM resource share in consumer account and create Glue resource link.")

        # Check KMS access
        has_kms = any(k.get("allows_principal", False) for k in kms_keys) if kms_keys else True
        if has_kms:
            effective_path.append("kms:Decrypt")
        else:
            missing.append(
                PermissionEdge(
                    source_node=principal_arn,
                    target_node="kms:key",
                    permission_type="kms_decrypt",
                    status="missing",
                    evidence="Principal missing in KMS Key Policy",
                )
            )
            recommendations.append("Add principal role ARN to KMS Key Policy `kms:Decrypt` statement.")

        is_accessible = len(missing) == 0

        return PermissionGraphAnalysis(
            principal_arn=principal_arn,
            target_table_arn=target_table,
            is_accessible=is_accessible,
            effective_path=effective_path if is_accessible else [],
            missing_permissions=missing,
            blocking_permissions=blocking,
            recommended_actions=recommendations,
        )
