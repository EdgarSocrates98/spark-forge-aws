"""Iceberg Table Doctor for Health Diagnosis and Metadata Inspection."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class IcebergHealthReport:
    table_name: str
    format_version: int
    health_score: int  # 0 - 100
    snapshot_count: int
    data_file_count: int
    delete_file_count: int
    small_file_count: int
    delete_file_ratio: float
    critical_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IcebergTableDoctor:
    """Diagnoses Iceberg tables from metadata dumps or online catalog inspection."""

    def diagnose_table(self, metadata: dict[str, Any]) -> IcebergHealthReport:
        table_name = metadata.get("table_name", "unknown")
        format_version = metadata.get("format_version", 2)
        snapshots = metadata.get("snapshots", [])
        data_files = metadata.get("data_files", [])
        delete_files = metadata.get("delete_files", [])
        small_file_threshold_mb = metadata.get("small_file_threshold_mb", 64)

        data_count = len(data_files)
        delete_count = len(delete_files)
        snapshot_count = len(snapshots)

        small_files = [f for f in data_files if f.get("file_size_in_bytes", 0) < small_file_threshold_mb * 1024 * 1024]
        small_count = len(small_files)

        total_files = max(1, data_count + delete_count)
        del_ratio = round(delete_count / total_files, 4)

        criticals = []
        warnings = []
        recs = []

        # Check delete files ratio
        if del_ratio > 0.15:
            criticals.append(f"High delete file ratio ({del_ratio*100:.1f}%). Read performance degraded.")
            recs.append("Run Iceberg row-level merge compaction (`rewrite_data_files` with delete file compaction).")
        elif del_ratio > 0.05:
            warnings.append(f"Moderate delete file ratio ({del_ratio*100:.1f}%).")
            recs.append("Schedule compaction maintenance.")

        # Check small files
        if small_count > 50:
            warnings.append(f"{small_count} small data files (<{small_file_threshold_mb}MB) found.")
            recs.append("Execute binpack compaction: `CALL glue_catalog.system.rewrite_data_files(table => '...')`.")

        # Check snapshot accumulation
        if snapshot_count > 100:
            warnings.append(f"{snapshot_count} active snapshots detected. Manifest metadata overhead increasing.")
            recs.append("Expire snapshots older than retention policy via `expire_snapshots`.")

        score = 100 - (len(criticals) * 35) - (len(warnings) * 15)
        score = max(0, min(100, score))

        return IcebergHealthReport(
            table_name=table_name,
            format_version=format_version,
            health_score=score,
            snapshot_count=snapshot_count,
            data_file_count=data_count,
            delete_file_count=delete_count,
            small_file_count=small_count,
            delete_file_ratio=del_ratio,
            critical_issues=criticals,
            warnings=warnings,
            recommendations=recs,
        )
