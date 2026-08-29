"""Iceberg Maintenance Planning Engine with Dry-Run Safety."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class MaintenanceAction:
    action_type: str  # rewrite_data_files, expire_snapshots, remove_orphan_files, rewrite_manifests
    sql_command: str
    target_table: str
    estimated_impact: str
    risk_level: str = "reversible"


@dataclass
class IcebergMaintenancePlan:
    table_name: str
    actions: list[MaintenanceAction]
    is_dry_run: bool = True
    approval_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IcebergMaintenancePlanner:
    """Generates deterministic, executable SQL maintenance plans for Iceberg tables."""

    def generate_plan(
        self,
        table_name: str,
        small_files_count: int = 0,
        delete_files_count: int = 0,
        snapshots_count: int = 0,
        retention_days: int = 7,
    ) -> IcebergMaintenancePlan:
        actions = []

        if small_files_count > 20 or delete_files_count > 5:
            actions.append(
                MaintenanceAction(
                    action_type="rewrite_data_files",
                    sql_command=(
                        f"CALL glue_catalog.system.rewrite_data_files(table => '{table_name}', "
                        f"strategy => 'binpack', options => "
                        f"map('target-file-size-bytes','536870912'))"
                    ),
                    target_table=table_name,
                    estimated_impact=(
                        f"Compact {small_files_count} data files and purge {delete_files_count} "
                        f"positional delete files."
                    ),
                    risk_level="reversible",
                )
            )

        if snapshots_count > 50:
            actions.append(
                MaintenanceAction(
                    action_type="expire_snapshots",
                    sql_command=(
                        f"CALL glue_catalog.system.expire_snapshots("
                        f"table => '{table_name}', older_than "
                        f"=> TIMESTAMP 'current_timestamp - INTERVAL {retention_days} DAYS')"
                    ),
                    target_table=table_name,
                    estimated_impact=(
                        f"Expire snapshots older than {retention_days} days to reduce manifest "
                        f"size."
                    ),
                    risk_level="reversible",
                )
            )

        actions.append(
            MaintenanceAction(
                action_type="rewrite_manifests",
                sql_command=f"CALL glue_catalog.system.rewrite_manifests(table => '{table_name}')",
                target_table=table_name,
                estimated_impact=(
                    "Re-cluster manifest entries to optimize Athena and Spark planning time."
                ),
                risk_level="reversible",
            )
        )

        return IcebergMaintenancePlan(
            table_name=table_name,
            actions=actions,
            is_dry_run=True,
            approval_required=True,
        )
