"""Apache Kafka and Amazon MSK Diagnostic Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class KafkaDiagnosticReport:
    topic_name: str
    consumer_group: str
    has_high_lag: bool
    has_partition_imbalance: bool
    under_replicated_partitions: int
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KafkaMSKSpecialist:
    """Diagnoses consumer lag, partition skew, and broker health in Kafka / MSK."""

    def diagnose_consumer_lag(
        self,
        topic_name: str,
        consumer_group: str,
        partition_lags: dict[int, int],
        under_replicated_count: int = 0,
    ) -> KafkaDiagnosticReport:
        recs = []
        lags = list(partition_lags.values())
        max_lag = max(lags) if lags else 0
        min_lag = min(lags) if lags else 0

        high_lag = max_lag > 50000
        imbalance = (max_lag - min_lag) > 20000 if len(lags) > 1 else False

        if high_lag:
            recs.append(
                f"High consumer lag detected (max: {max_lag} records). "
                f"Scale consumer group instances "
                f"or optimize downstream sink."
            )

        if imbalance:
            recs.append(
                f"Partition lag imbalance detected ({min_lag} to {max_lag}). Verify partition "
                f"key distribution and hash randomness."
            )

        if under_replicated_count > 0:
            recs.append(
                f"{under_replicated_count} under-replicated partitions found. Check MSK broker "
                f"disk/network health."
            )

        return KafkaDiagnosticReport(
            topic_name=topic_name,
            consumer_group=consumer_group,
            has_high_lag=high_lag,
            has_partition_imbalance=imbalance,
            under_replicated_partitions=under_replicated_count,
            recommendations=recs,
        )
