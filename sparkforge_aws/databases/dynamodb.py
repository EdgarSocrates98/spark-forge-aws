"""DynamoDB Specialization and Access Pattern Diagnostic Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DynamoDBHealthReport:
    table_name: str
    billing_mode: str
    has_hot_partition_risk: bool
    has_gsi_throttling_risk: bool
    is_streams_enabled: bool
    is_ttl_enabled: bool
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DynamoDBSpecialist:
    """Diagnoses DynamoDB single-table schema, capacity, and partition skew."""

    def analyze_table_config(self, config: dict[str, Any]) -> DynamoDBHealthReport:
        table_name = config.get("TableName", "unknown")
        billing = config.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")
        pk = config.get("KeySchema", [{}])[0].get("AttributeName", "")

        recs = []
        hot_partition = False
        gsi_throttling = False

        # Hot partition check (e.g. low-cardinality PK like 'status' or 'country')
        if pk.lower() in ("status", "type", "category", "country", "date", "created_date"):
            hot_partition = True
            recs.append(
                f"Low-cardinality partition key ('{pk}') creates hot partition risks. "
                f"Add a high-cardinality "
                f"prefix/suffix or synthetic key."
            )

        gsis = config.get("GlobalSecondaryIndexes", [])
        if billing == "PROVISIONED":
            # Check GSI capacity imbalance
            table_wcu = config.get("ProvisionedThroughput", {}).get("WriteCapacityUnits", 5)
            for gsi in gsis:
                gsi_wcu = gsi.get("ProvisionedThroughput", {}).get("WriteCapacityUnits", 5)
                if gsi_wcu < table_wcu:
                    gsi_throttling = True
                    recs.append(
                        f"GSI '{gsi.get('IndexName')}' has lower WCU ({gsi_wcu}) than main table "
                        f"({table_wcu}), causing main table writes to throttle."
                    )

        stream_spec = config.get("StreamSpecification", {})
        streams_enabled = stream_spec.get("StreamEnabled", False)
        ttl_enabled = (
            config.get("TimeToLiveDescription", {}).get("TimeToLiveStatus", "") == "ENABLED"
        )

        if not ttl_enabled:
            recs.append(
                "TTL is not configured. Consider enabling TTL for automatic data expiration to "
                "optimize storage costs."
            )

        return DynamoDBHealthReport(
            table_name=table_name,
            billing_mode=billing,
            has_hot_partition_risk=hot_partition,
            has_gsi_throttling_risk=gsi_throttling,
            is_streams_enabled=streams_enabled,
            is_ttl_enabled=ttl_enabled,
            recommendations=recs,
        )
