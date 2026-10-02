"""Contract tests for the complete Forge Lab product.

These tests are intentionally held until the final delivery pass for this
prompt. They stay executable and are not replaced by smoke-only assertions.
"""

from __future__ import annotations

from pathlib import Path

from sparkforge.lab.contract import load_version_registry
from sparkforge.lab.scenario import load_scenario_suite


ROOT = Path(__file__).parents[1]


def test_registry_and_scenario_contracts_are_pinned() -> None:
    registry = load_version_registry(ROOT / "lab" / "versions.yaml")
    suite = load_scenario_suite(ROOT / "lab" / "scenarios" / "golden.yaml")

    assert registry.schema_version == 1
    assert registry.defaults
    assert all("latest" not in value.lower() for value in registry.serialized_values())
    assert len(suite.scenarios) == 20
    assert {scenario.fidelity.tier for scenario in suite.scenarios} <= {"L0", "L1", "L2", "L3"}


def test_golden_scenarios_compile_to_reusable_actions() -> None:
    suite = load_scenario_suite(ROOT / "lab" / "scenarios" / "golden.yaml")

    for scenario in suite.scenarios:
        actions = scenario.compile_actions()
        kinds = [action.kind for action in actions]
        assert kinds[0] == "seed_dataset"
        assert "capture_baseline" in kinds
        assert "compare_oracle" in kinds
        assert kinds[-1] == "receipt"


def test_runtime_backends_share_plan_and_mutations_are_guarded() -> None:
    from sparkforge.lab.runtime import build_runtime_plan

    scenario = load_scenario_suite(ROOT / "lab" / "scenarios" / "golden.yaml").by_id("LAB-004")
    compose = build_runtime_plan(scenario, backend="compose")
    testcontainers = build_runtime_plan(scenario, backend="testcontainers")

    assert compose.actions == testcontainers.actions
    assert build_runtime_plan(scenario, backend="compose", execute=False).requires_confirmation


def test_receipt_oracle_and_equivalence_are_independent(tmp_path: Path) -> None:
    from sparkforge.lab.evidence import compare_oracle, create_run, finalize_receipt
    from sparkforge.lab.oracle import ExpectedOracle

    scenario = load_scenario_suite(ROOT / "lab" / "scenarios" / "golden.yaml").by_id("LAB-004")
    run = create_run(tmp_path, scenario, seed=42)
    oracle = ExpectedOracle.from_scenario(scenario)
    result = compare_oracle(
        oracle,
        facts=[{"kind": item} for item in oracle.expected_facts],
        findings=[{"rule_id": item} for item in oracle.expected_findings],
    )
    receipt = finalize_receipt(run, result)

    assert result.classification in {"PASS", "UNRESOLVED"}
    assert receipt["receipt_sha256"]
    assert receipt["oracle_source"] == "scenario.expected"


def test_cli_exposes_lab_product_commands() -> None:
    from sparkforge.adapters.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["lab", "doctor", "--repo", "."])
    assert args.command == "lab"
    assert args.lab_action == "doctor"


def test_lab_documentation_states_fidelity_boundaries() -> None:
    text = (ROOT / "docs" / "knowledge" / "forge-lab-product.md").read_text(encoding="utf-8")
    assert "does_not_prove" in text
    assert "L3" in text
    assert "latest" in text
