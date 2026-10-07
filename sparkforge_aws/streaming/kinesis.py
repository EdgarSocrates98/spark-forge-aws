"""Amazon Kinesis Data Streams Diagnostic Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class KinesisHealthReport:
    stream_name: str
    shard_count: int
    has_hot_shards: bool
    is_enhanced_fanout_recommended: bool
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KinesisSpecialist:
    """Diagnoses Kinesis shard capacity, hot shards, and consumer fan-out."""

    def diagnose_stream(
        self,
        stream_name: str,
        shard_count: int,
        shard_throughput_mb_sec: dict[str, float],
        consumer_count: int = 1,
    ) -> KinesisHealthReport:
        recs = []
        hot_shards = False

        for sid, tput in shard_throughput_mb_sec.items():
            if tput > 0.85:  # Kinesis limit is 1MB/sec write per shard
                hot_shards = True
                recs.append(
                    f"Shard '{sid}' is near 1MB/sec write limit ({tput:.2f}MB/s). Partition key "
                    f"entropy is too low."
                )

        fanout_rec = consumer_count >= 3
        if fanout_rec:
            recs.append(
                f"{consumer_count} concurrent consumers detected. Enable Enhanced Fan-Out (EFO) "
                f"with dedicated 2MB/sec per consumer pipe."
            )

        return KinesisHealthReport(
            stream_name=stream_name,
            shard_count=shard_count,
            has_hot_shards=hot_shards,
            is_enhanced_fanout_recommended=fanout_rec,
            recommendations=recs,
        )
