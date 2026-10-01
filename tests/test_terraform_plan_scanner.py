"""Tests for Terraform Plan Risk Scanner."""

from sparkforge.terraform.plan_analyzer import TerraformPlanAnalyzer


def test_terraform_plan_safe_create():
    analyzer = TerraformPlanAnalyzer()
    plan = {
        "resource_changes": [
            {
                "address": "aws_s3_bucket.new_lake",
                "type": "aws_s3_bucket",
                "change": {"actions": ["create"]},
            }
        ]
    }
    report = analyzer.analyze_plan_json(plan)
    assert report.total_creates == 1
    assert report.overall_risk == "SAFE"
    assert report.has_data_loss_risk is False


def test_terraform_plan_block_stateful_delete():
    analyzer = TerraformPlanAnalyzer()
    plan = {
        "resource_changes": [
            {
                "address": "aws_s3_bucket.prod_lake",
                "type": "aws_s3_bucket",
                "change": {"actions": ["delete"]},
            }
        ]
    }
    report = analyzer.analyze_plan_json(plan)
    assert report.total_deletes == 1
    assert report.overall_risk == "BLOCK"
    assert report.has_data_loss_risk is True
