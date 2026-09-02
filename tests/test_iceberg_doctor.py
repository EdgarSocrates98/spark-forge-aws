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


def test_o_planner_nao_julga_mais_por_contagem_crua():
    """`generate_plan(small_files_count=..., ...)` foi REMOVIDO em 2026-09-02.

    Ele decidia com `> 20`, `> 5` e `> 50` -- quatro numeros sem fonte, dos
    quais tres duplicavam `SF-ICE-001`, `SF-ICE-002` e `SF-ICE-003`, que ja
    julgam a mesma coisa com `severity_by` medido e `sources` citadas.

    O que substitui esta em `tests/test_iceberg_maintenance.py`: o plano deriva
    dos ACHADOS, e o limiar mora na regra.
    """
    planner = IcebergMaintenancePlanner()
    assert not hasattr(planner, "generate_plan"), (
        "o metodo que julgava por contagem crua voltou. O limiar mora na regra."
    )
    assert hasattr(planner, "plan_from_findings")
