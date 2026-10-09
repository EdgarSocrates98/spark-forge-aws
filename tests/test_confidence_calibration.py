from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sparkforge_aws.decision.calibration import (
    CalibrationError,
    HistoricalCalibrator,
    load_cases,
)

ROOT = Path(__file__).resolve().parents[1]


def _history():
    raw = yaml.safe_load(
        (ROOT / "evals/token_efficient/fixtures/calibration_history.yaml").read_text(
            encoding="utf-8"
        )
    )
    return load_cases(raw["cases"])


def test_calibration_emits_raw_calibrated_method_provenance_and_holdout() -> None:
    cases = _history()
    calibrator = HistoricalCalibrator()
    artifact = calibrator.fit(cases, version="control-plane-calibration-v1")
    evaluations = calibrator.evaluate(artifact, cases)
    assert len(evaluations) == len(cases)
    assert all(item.method == "isotonic_pava_v1" for item in evaluations)
    assert all("artifact_hash" in item.provenance for item in evaluations)
    assert sum(item.holdout for item in evaluations) == 4
    assert calibrator.holdout_metrics(artifact, cases)["count"] == 4


def test_online_update_is_refused_and_artifact_stays_unchanged() -> None:
    artifact = HistoricalCalibrator().fit(_history(), version="v1")
    before = artifact.to_dict()
    with pytest.raises(CalibrationError, match="calibration_online_update_refused"):
        artifact.update({"case_id": "online"})
    assert artifact.to_dict() == before


def test_holdout_cases_do_not_change_fit_artifact() -> None:
    cases = _history()
    calibrator = HistoricalCalibrator()
    artifact = calibrator.fit(cases, version="v1")
    without_holdout = calibrator.fit(
        tuple(case for case in cases if case.partition == "train"), version="v1"
    )
    assert artifact.calibrated_values == without_holdout.calibrated_values
    assert artifact.train_case_ids == without_holdout.train_case_ids
