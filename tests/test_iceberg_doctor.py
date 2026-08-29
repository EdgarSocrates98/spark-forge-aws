"""Tests for Iceberg Table Doctor and Maintenance Planner."""
from sparkforge.iceberg.doctor import IcebergTableDoctor
from sparkforge.iceberg.maintenance import IcebergMaintenancePlanner


def test_iceberg_table_doctor_degraded():
    doctor = IcebergTableDoctor()
    meta = {
        "table_name": "db.orders_iceberg",
        "format_version": 2,
        "snapshots": [{} for _ in range(120)],
        "data_files": [{"file_size_in_bytes": 10 * 1024 * 1024} for _ in range(60)],
        "delete_files": [{} for _ in range(20)],
    }
    report = doctor.diagnose_table(meta)
    assert report.health_score < 70
    assert report.delete_file_ratio > 0.15
    assert len(report.critical_issues) > 0
    assert len(report.warnings) > 0


def test_iceberg_maintenance_plan():
    planner = IcebergMaintenancePlanner()
    plan = planner.generate_plan(
        table_name="db.orders_iceberg",
        small_files_count=60,
        delete_files_count=20,
        snapshots_count=120,
        retention_days=7,
    )
    assert len(plan.actions) >= 3
    assert any(a.action_type == "rewrite_data_files" for a in plan.actions)
    assert any(a.action_type == "expire_snapshots" for a in plan.actions)
    assert any(a.action_type == "rewrite_manifests" for a in plan.actions)
    assert plan.is_dry_run is True
