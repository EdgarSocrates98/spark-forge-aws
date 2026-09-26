"""Facts for already observed Athena cost measurements."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "athena_cost@0.1.0"
EMITTED_KINDS = frozenset({"athena.query_cost", "athena.query_cost.unresolved"})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _subject(entry: Mapping[str, Any]) -> dict[str, Any]:
    query_id = entry.get("query_id", entry.get("id", entry.get("symbol", "")))
    return {"type": "job_run", "symbol": str(query_id or "")}


def extract_athena_cost(payload: Mapping[str, Any], path: str, artifact_sha256: str = "") -> list[Fact]:
    entries = payload.get("costs", [payload])
    if not isinstance(entries, list):
        entries = [payload]
    facts: list[Fact] = []
    provenance = {"extractor": EXTRACTOR_ID, "artifact": path, "artifact_sha256": artifact_sha256}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        subject = _subject(entry)
        cost = entry.get("cost")
        basis = entry.get("cost_basis")
        if not isinstance(cost, int | float) or isinstance(cost, bool) or not isinstance(basis, str) or not basis.strip():
            facts.append(
                Fact(
                    kind="athena.query_cost.unresolved",
                    subject=subject,
                    attrs={"reason": "measurement_or_cost_basis_missing"},
                    provenance=provenance,
                )
            )
            continue
        measures: dict[str, Any] = {"cost": float(cost)}
        bytes_scanned = entry.get("bytes_scanned")
        if isinstance(bytes_scanned, int | float) and not isinstance(bytes_scanned, bool):
            measures["bytes_scanned"] = float(bytes_scanned)
        attrs = {
            "currency": str(entry.get("currency") or ""),
            "cost_basis": basis.strip(),
            "observed_at": str(entry.get("observed_at") or ""),
        }
        facts.append(Fact(kind="athena.query_cost", subject=subject, measures=measures, attrs=attrs, provenance=provenance))
    return sort_facts(facts)


def extract_athena_cost_path(path: str | Path) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    payload = json.loads(target.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, Mapping):
        raise ValueError("custo Athena precisa ser um objeto")
    return extract_athena_cost(payload, str(target), _sha256(target))
