"""Tests for Lake Formation Permission Graph and Doctor."""
from sparkforge.lakeformation.doctor import LakeFormationDoctor
from sparkforge.lakeformation.graph import LakeFormationPermissionGraph


def test_permission_graph_accessible():
    graph = LakeFormationPermissionGraph()
    grants = [{"table": "analytics_db.sales", "permissions": ["SELECT"]}]
    ram = [{"status": "ACCEPTED"}]
    kms = [{"allows_principal": True}]

    res = graph.evaluate_access(
        principal_arn="arn:aws:iam::123456789012:role/GlueJobRole",
        target_table="analytics_db.sales",
        grants=grants,
        ram_shares=ram,
        kms_keys=kms,
        is_cross_account=True,
    )
    assert res.is_accessible is True
    assert len(res.missing_permissions) == 0


def test_permission_graph_missing_grant():
    graph = LakeFormationPermissionGraph()
    res = graph.evaluate_access(
        principal_arn="arn:aws:iam::123456789012:role/GlueJobRole",
        target_table="analytics_db.sales",
        grants=[],
        ram_shares=[],
        kms_keys=[],
        is_cross_account=False,
    )
    assert res.is_accessible is False
    assert len(res.missing_permissions) > 0


def test_lakeformation_doctor_cross_account():
    doctor = LakeFormationDoctor()
    dump = {
        "ram_share_status": "PENDING",
        "resource_link_exists": False,
        "kms_key_policy_includes_consumer": False,
    }
    report = doctor.diagnose_cross_account(dump)
    assert report.health_score < 50
    assert len(report.fail_items) >= 2
    assert len(report.recommendations) >= 2


def test_access_model_advisor():
    doctor = LakeFormationDoctor()
    adv_fta = doctor.recommend_access_model(has_row_filters=False, has_column_filters=False)
    assert adv_fta["model"] == "FTA"

    adv_fgac = doctor.recommend_access_model(has_row_filters=True, has_column_filters=False)
    assert adv_fgac["model"] == "FGAC"
