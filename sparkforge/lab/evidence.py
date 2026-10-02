"""Artifact capture, receipts, oracle comparison and fixture promotion."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .contract import LabContractError
from .oracle import ExpectedOracle, OracleResult


RUN_DIRECTORIES = ("input", "logs", "metrics", "spark", "kafka", "flink", "iceberg", "cdc", "facts", "findings")


def create_run(
    root: str | Path,
    scenario: Any,
    *,
    seed: int,
    environment: dict[str, Any] | None = None,
    versions: dict[str, Any] | None = None,
) -> Path:
    base = Path(root).expanduser().resolve() / ".sparkforge" / "lab" / "runs"
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:12]}"
    run = base / run_id
    run.mkdir(parents=True, exist_ok=False)
    for directory in RUN_DIRECTORIES:
        (run / directory).mkdir()
    (run / "scenario.yaml").write_text(yaml.safe_dump(scenario.to_dict(), sort_keys=False), encoding="utf-8")
    (run / "environment.json").write_text(_json(environment or {"platform": os.name}), encoding="utf-8")
    (run / "versions.json").write_text(_json(versions or {"status": "unresolved_until_runtime"}), encoding="utf-8")
    run_record = {
        "run_id": run_id,
        "scenario": scenario.scenario_id,
        "scenario_version": scenario.version,
        "scenario_fingerprint": scenario.fingerprint,
        "seed": seed,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "created",
        "fidelity": scenario.fidelity.to_dict(),
    }
    (run / "run.json").write_text(_json(run_record), encoding="utf-8")
    (run / "topology.json").write_text(_json(scenario.topology), encoding="utf-8")
    return run


def capture_artifact(run: str | Path, source: str | Path, *, category: str, name: str | None = None) -> dict[str, Any]:
    run_path = Path(run).expanduser().resolve()
    if category not in RUN_DIRECTORIES:
        raise LabContractError(f"unsupported artifact category: {category}")
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise LabContractError(f"artifact source not found: {source}")
    destination = run_path / category / (name or source_path.name)
    if destination.name in {"", ".", ".."} or destination.parent != (run_path / category):
        raise LabContractError("artifact destination must remain in category root")
    shutil.copy2(source_path, destination)
    return {"category": category, "path": destination.relative_to(run_path).as_posix(), "sha256": _sha256(destination), "bytes": destination.stat().st_size}


def compare_oracle(oracle: ExpectedOracle, *, facts: list[dict[str, Any]], findings: list[dict[str, Any]], unresolved: list[str] | None = None) -> OracleResult:
    return oracle.compare(facts, findings, unresolved)


def finalize_receipt(
    run: str | Path,
    result: OracleResult,
    *,
    facts: list[dict[str, Any]] | None = None,
    findings: list[dict[str, Any]] | None = None,
    faults: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    run_path = Path(run).expanduser().resolve()
    run_record = _read_json(run_path / "run.json")
    payload = {
        "schema_version": 1,
        "run_id": run_record["run_id"],
        "scenario": run_record["scenario"],
        "scenario_version": run_record["scenario_version"],
        "scenario_fingerprint": run_record["scenario_fingerprint"],
        "sparkforge_commit": "unresolved_without_host_commit",
        "lab_commit": "unresolved_without_host_commit",
        "environment": _read_json(run_path / "environment.json"),
        "versions": _read_json(run_path / "versions.json"),
        "seed": run_record["seed"],
        "started_at": run_record["started_at"],
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "fidelity": run_record["fidelity"],
        "faults": faults or [],
        "artifacts": _list_artifacts(run_path),
        "facts": facts or [],
        "findings": findings or [],
        "oracle_source": "scenario.expected",
        "oracle": result.to_dict(),
        "assertions": {"passed": result.classification == "PASS", "failed": result.classification == "FAIL", "classification": result.classification},
    }
    payload["receipt_sha256"] = _sha256_bytes(_canonical(payload).encode("utf-8"))
    (run_path / "receipt.json").write_text(_json(payload), encoding="utf-8")
    run_record["status"] = result.classification
    run_record["finished_at"] = payload["finished_at"]
    (run_path / "run.json").write_text(_json(run_record), encoding="utf-8")
    return payload


def verify_receipt(path: str | Path) -> dict[str, Any]:
    payload = _read_json(Path(path))
    expected = payload.get("receipt_sha256")
    without_hash = dict(payload)
    without_hash.pop("receipt_sha256", None)
    actual = _sha256_bytes(_canonical(without_hash).encode("utf-8"))
    return {"valid": expected == actual, "expected": expected, "actual": actual}


def promote_fixture(run: str | Path, destination: str | Path, *, reviewed: bool = False) -> dict[str, Any]:
    if not reviewed:
        raise LabContractError("fixture promotion requires reviewed=True")
    run_path = Path(run).expanduser().resolve()
    receipt = run_path / "receipt.json"
    verification = verify_receipt(receipt)
    if not verification["valid"]:
        raise LabContractError("fixture promotion refused: receipt hash mismatch")
    target = Path(destination).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=False)
    copied = []
    for relative in ("scenario.yaml", "receipt.json", "facts", "findings"):
        source = run_path / relative
        destination_path = target / relative
        if source.is_dir():
            shutil.copytree(source, destination_path)
        elif source.is_file():
            shutil.copy2(source, destination_path)
        else:
            continue
        copied.append(relative)
    return {"promoted": True, "source": run_path.as_posix(), "destination": target.as_posix(), "receipt": verification, "paths": copied}


def _list_artifacts(run: Path) -> list[dict[str, Any]]:
    result = []
    for root, directories, files in os.walk(run):
        directories.sort()
        for filename in sorted(files):
            path = Path(root) / filename
            if path.name != "receipt.json":
                result.append(
                    {
                        "path": path.relative_to(run).as_posix(),
                        "sha256": _sha256(path),
                        "bytes": path.stat().st_size,
                    }
                )
    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabContractError(f"invalid lab JSON: {path}") from exc
    if not isinstance(value, dict):
        raise LabContractError(f"lab JSON must be an object: {path}")
    return value


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


__all__ = ["RUN_DIRECTORIES", "capture_artifact", "compare_oracle", "create_run", "finalize_receipt", "promote_fixture", "verify_receipt"]
