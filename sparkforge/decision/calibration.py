"""Offline historical confidence calibration with immutable artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sparkforge.decision.fingerprint import digest

CALIBRATION_SCHEMA_VERSION = 1
CALIBRATION_METHOD = "isotonic_pava_v1"


class CalibrationError(ValueError):
    """Named calibration contract error."""


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    case_id: str
    raw_confidence: float
    label: int
    partition: str
    source_hash: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CalibrationCase:
        case_id = str(raw.get("case_id", "")).strip()
        partition = str(raw.get("partition", "")).strip()
        source_hash = str(raw.get("source_hash", "")).strip()
        raw_confidence = raw.get("raw_confidence")
        label = raw.get("label")
        if not case_id or partition not in {"train", "holdout"} or not source_hash:
            raise CalibrationError("calibration_case_invalid:identity")
        if isinstance(raw_confidence, bool) or not isinstance(raw_confidence, (int, float)):
            raise CalibrationError(f"calibration_case_invalid:{case_id}.raw_confidence")
        if not 0.0 <= float(raw_confidence) <= 1.0:
            raise CalibrationError(f"calibration_case_invalid:{case_id}.raw_confidence")
        if label not in (0, 1):
            raise CalibrationError(f"calibration_case_invalid:{case_id}.label")
        return cls(case_id, float(raw_confidence), int(label), partition, source_hash)

    def canonical(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "raw_confidence": self.raw_confidence,
            "label": self.label,
            "partition": self.partition,
            "source_hash": self.source_hash,
        }


@dataclass(frozen=True, slots=True)
class CalibrationArtifact:
    schema_version: int
    method: str
    version: str
    train_case_ids: tuple[str, ...]
    holdout_case_ids: tuple[str, ...]
    breakpoints: tuple[float, ...]
    calibrated_values: tuple[float, ...]
    source_hash: str
    artifact_hash: str

    def __post_init__(self) -> None:
        if len(self.breakpoints) != len(self.calibrated_values) or not self.breakpoints:
            raise CalibrationError("calibration_artifact_invalid:breakpoints")
        if any(not 0.0 <= value <= 1.0 for value in self.calibrated_values):
            raise CalibrationError("calibration_artifact_invalid:values")

    def calibrate(self, raw_confidence: float) -> float:
        if not 0.0 <= raw_confidence <= 1.0:
            raise CalibrationError("raw_confidence must be between 0 and 1")
        for breakpoint, value in zip(self.breakpoints, self.calibrated_values, strict=True):
            if raw_confidence <= breakpoint:
                return value
        return self.calibrated_values[-1]

    def update(self, *_: object) -> None:
        raise CalibrationError("calibration_online_update_refused")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "method": self.method,
            "version": self.version,
            "train_case_ids": list(self.train_case_ids),
            "holdout_case_ids": list(self.holdout_case_ids),
            "breakpoints": list(self.breakpoints),
            "calibrated_values": list(self.calibrated_values),
            "source_hash": self.source_hash,
            "artifact_hash": self.artifact_hash,
        }


@dataclass(frozen=True, slots=True)
class CalibrationEvaluation:
    case_id: str
    raw_confidence: float
    calibrated_confidence: float
    method: str
    version: str
    provenance: dict[str, Any]
    holdout: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "raw_confidence": self.raw_confidence,
            "calibrated_confidence": self.calibrated_confidence,
            "method": self.method,
            "version": self.version,
            "provenance": self.provenance,
            "holdout": self.holdout,
        }


class HistoricalCalibrator:
    """Fit a deterministic monotonic calibration artifact offline."""

    def fit(self, cases: Iterable[CalibrationCase], *, version: str) -> CalibrationArtifact:
        values = tuple(cases)
        if not version.strip():
            raise CalibrationError("calibration_version_required")
        if not values:
            raise CalibrationError("calibration_history_empty")
        if len({case.case_id for case in values}) != len(values):
            raise CalibrationError("calibration_case_ids_must_be_unique")
        train = tuple(sorted((case for case in values if case.partition == "train"), key=_sort_key))
        holdout = tuple(
            sorted((case for case in values if case.partition == "holdout"), key=_sort_key)
        )
        if not train:
            raise CalibrationError("calibration_train_empty")
        breakpoints, calibrated = _pava(train)
        source_hash = digest([case.canonical() for case in values])
        artifact_body = {
            "schema_version": CALIBRATION_SCHEMA_VERSION,
            "method": CALIBRATION_METHOD,
            "version": version,
            "train_case_ids": [case.case_id for case in train],
            "holdout_case_ids": [case.case_id for case in holdout],
            "breakpoints": breakpoints,
            "calibrated_values": calibrated,
            "source_hash": source_hash,
        }
        return CalibrationArtifact(
            **artifact_body,
            artifact_hash=digest(artifact_body),
        )

    def evaluate(
        self, artifact: CalibrationArtifact, cases: Iterable[CalibrationCase]
    ) -> tuple[CalibrationEvaluation, ...]:
        result = []
        for case in cases:
            result.append(
                CalibrationEvaluation(
                    case_id=case.case_id,
                    raw_confidence=case.raw_confidence,
                    calibrated_confidence=artifact.calibrate(case.raw_confidence),
                    method=artifact.method,
                    version=artifact.version,
                    provenance={
                        "source_hash": case.source_hash,
                        "artifact_hash": artifact.artifact_hash,
                        "training_cases": list(artifact.train_case_ids),
                        "holdout_cases": list(artifact.holdout_case_ids),
                    },
                    holdout=case.partition == "holdout",
                )
            )
        return tuple(result)

    def holdout_metrics(
        self, artifact: CalibrationArtifact, cases: Iterable[CalibrationCase]
    ) -> dict[str, Any]:
        holdout = tuple(case for case in cases if case.partition == "holdout")
        evaluations = self.evaluate(artifact, holdout)
        brier = (
            sum(
                (item.calibrated_confidence - case.label) ** 2
                for item, case in zip(evaluations, holdout, strict=True)
            )
            / len(holdout)
            if holdout
            else None
        )
        return {
            "count": len(holdout),
            "brier_score": brier,
            "holdout_case_ids": [case.case_id for case in holdout],
            "artifact_hash": artifact.artifact_hash,
        }


def load_cases(raw: Iterable[Mapping[str, Any]]) -> tuple[CalibrationCase, ...]:
    return tuple(CalibrationCase.from_mapping(item) for item in raw)


def _sort_key(case: CalibrationCase) -> tuple[float, str]:
    return case.raw_confidence, case.case_id


def _pava(cases: tuple[CalibrationCase, ...]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    blocks: list[dict[str, float]] = []
    for case in cases:
        blocks.append(
            {
                "low": case.raw_confidence,
                "high": case.raw_confidence,
                "total": float(case.label),
                "weight": 1.0,
            }
        )
        while len(blocks) >= 2:
            left, right = blocks[-2], blocks[-1]
            left_value = left["total"] / left["weight"]
            right_value = right["total"] / right["weight"]
            if left_value <= right_value:
                break
            blocks[-2] = {
                "low": left["low"],
                "high": right["high"],
                "total": left["total"] + right["total"],
                "weight": left["weight"] + right["weight"],
            }
            blocks.pop()
    return (
        tuple(block["high"] for block in blocks),
        tuple(block["total"] / block["weight"] for block in blocks),
    )


__all__ = [
    "CALIBRATION_METHOD",
    "CalibrationArtifact",
    "CalibrationCase",
    "CalibrationError",
    "CalibrationEvaluation",
    "HistoricalCalibrator",
    "load_cases",
]
