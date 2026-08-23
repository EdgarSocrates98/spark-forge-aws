"""Tests for SparkForge Evaluation Framework (Phase 8)."""
from pathlib import Path
import pytest

from sparkforge.evals import EvaluationRunner


def test_router_golden_eval_dataset():
    dataset_path = Path(__file__).parent.parent / "sparkforge" / "evals" / "datasets" / "router_dataset.json"
    assert dataset_path.is_file()

    runner = EvaluationRunner()
    result = runner.run_router_eval(dataset_path)

    assert result.total_cases == 4
    assert result.failed_cases == 0
    assert result.pass_rate == 1.0
