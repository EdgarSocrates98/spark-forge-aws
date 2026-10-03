"""Offline architecture decision support for streaming workloads.

This module evaluates only declared requirements and a versioned candidate
capability table. It does not rank platforms by preference, estimate cost, or
pretend that an assumption is a fact. A winner is emitted only when hard
constraints leave exactly one viable candidate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ENGINE_VERSION = "streaming_architecture@0.1.0"

# This is intentionally a small hard-constraint table. Claims belong in the
# knowledge document; the evaluator only uses capabilities that are explicit
# and stable enough to eliminate a candidate.
CANDIDATES: tuple[dict[str, Any], ...] = (
    {
        "name": "spark_structured_streaming",
        "role": "runtime",
        "managed": False,
        "stateful": True,
        "for_each_batch": True,
        "output_modes": ["append", "update", "complete"],
        "sources": ["kafka", "kinesis", "file", "socket"],
        "apis": ["spark", "structured_streaming"],
    },
    {
        "name": "glue_streaming",
        "role": "runtime",
        "managed": True,
        "stateful": True,
        "for_each_batch": True,
        "output_modes": ["append", "update", "complete"],
        "sources": ["kafka", "kinesis"],
        "apis": ["spark", "structured_streaming", "glue"],
    },
    {
        "name": "glue_rtm",
        "role": "runtime",
        "managed": True,
        "stateful": False,
        "for_each_batch": False,
        "output_modes": ["update"],
        "sources": ["kinesis", "kafka"],
        "apis": ["glue", "rtm"],
    },
    {
        "name": "apache_flink",
        "role": "runtime",
        "managed": False,
        "stateful": True,
        "for_each_batch": False,
        "output_modes": ["append", "update"],
        "sources": ["kafka", "kinesis", "file"],
        "apis": ["flink", "data_stream", "table"],
    },
    {
        "name": "managed_flink",
        "role": "runtime",
        "managed": True,
        "stateful": True,
        "for_each_batch": False,
        "output_modes": ["append", "update"],
        "sources": ["kafka", "kinesis"],
        "apis": ["flink", "data_stream", "table", "managed_flink"],
    },
    {
        "name": "kafka_streams",
        "role": "runtime",
        "managed": False,
        "stateful": True,
        "for_each_batch": False,
        "output_modes": ["update"],
        "sources": ["kafka"],
        "apis": ["kafka_streams"],
    },
    {
        "name": "iceberg_lakehouse",
        "role": "sink",
        "managed": False,
        "stateful": None,
        "for_each_batch": None,
        "output_modes": [],
        "sources": [],
        "apis": ["iceberg", "lakehouse"],
        "sink": "iceberg",
    },
    {
        "name": "redshift_streaming",
        "role": "sink",
        "managed": True,
        "stateful": None,
        "for_each_batch": None,
        "output_modes": [],
        "sources": [],
        "apis": ["redshift", "streaming_ingestion"],
        "sink": "redshift",
    },
)

_KNOWN_REQUIREMENTS = {
    "source",
    "sink",
    "stateful",
    "for_each_batch",
    "output_mode",
    "aws_managed_only",
    "engine_api",
    "latency_target_ms",
    "ordering_required",
    "exactly_once",
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _load_input(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise ValueError(f"Caminho nao encontrado para arquitetura streaming: {path}")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalido para arquitetura streaming: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("O artefato de arquitetura streaming precisa ser um objeto JSON")
    return value


def _declared_requirements(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    requirements = raw.get("requirements")
    unresolved: list[str] = []
    if requirements is None:
        unresolved.append("requirements_missing")
        requirements = {}
    if not isinstance(requirements, dict):
        unresolved.append("requirements_must_be_object")
        requirements = {}
    unknown = sorted(set(requirements) - _KNOWN_REQUIREMENTS)
    unresolved.extend(f"unknown_requirement:{key}" for key in unknown)
    return dict(requirements), unresolved


def _assumptions(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    assumptions = raw.get("assumptions", {})
    if assumptions is None:
        assumptions = {}
    if not isinstance(assumptions, dict):
        return {}, ["assumptions_must_be_object"]
    return dict(assumptions), []


def _requirement_facts(requirements: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "fact_id": f"requirement.{key}",
            "kind": "architecture.requirement",
            "name": key,
            "value": requirements[key],
            "evidence": "declared_input.requirements",
        }
        for key in sorted(requirements)
    ]


def _evaluate_candidate(candidate: dict[str, Any], requirements: dict[str, Any]) -> dict[str, Any]:
    constraints: list[dict[str, Any]] = []
    unresolved: list[str] = []
    evidence: list[str] = []

    role = candidate["role"]
    if role == "sink":
        sink = requirements.get("sink")
        if sink is None:
            unresolved.append("sink_missing")
        elif sink != candidate.get("sink"):
            constraints.append({"requirement": "sink", "expected": candidate.get("sink"), "observed": sink})
        else:
            evidence.append(f"sink={sink}")
    else:
        if requirements.get("sink") in {"iceberg", "redshift"}:
            evidence.append(f"runtime_can_pair_with_sink={requirements['sink']}")

        source = requirements.get("source")
        if source is None:
            unresolved.append("source_missing")
        elif source not in candidate["sources"]:
            constraints.append({"requirement": "source", "supported": candidate["sources"], "observed": source})
        else:
            evidence.append(f"source={source}")

        stateful = requirements.get("stateful")
        if stateful is None:
            unresolved.append("stateful_missing")
        elif stateful is True and candidate["stateful"] is False:
            constraints.append({"requirement": "stateful", "expected": True, "observed": False})
        elif stateful is False or candidate["stateful"] is True:
            evidence.append(f"stateful={stateful}")

        for_each_batch = requirements.get("for_each_batch")
        if for_each_batch is None:
            unresolved.append("for_each_batch_missing")
        elif for_each_batch is True and candidate["for_each_batch"] is False:
            constraints.append({"requirement": "for_each_batch", "expected": True, "observed": False})
        elif for_each_batch is False or candidate["for_each_batch"] is True:
            evidence.append(f"for_each_batch={for_each_batch}")

        output_mode = requirements.get("output_mode")
        if output_mode is None:
            unresolved.append("output_mode_missing")
        elif output_mode not in candidate["output_modes"]:
            constraints.append({"requirement": "output_mode", "supported": candidate["output_modes"], "observed": output_mode})
        else:
            evidence.append(f"output_mode={output_mode}")

        api = requirements.get("engine_api")
        if api is not None:
            if api not in candidate["apis"]:
                constraints.append({"requirement": "engine_api", "supported": candidate["apis"], "observed": api})
            else:
                evidence.append(f"engine_api={api}")

    managed_only = requirements.get("aws_managed_only")
    if managed_only is True:
        if candidate["managed"] is False:
            constraints.append({"requirement": "aws_managed_only", "expected": True, "observed": False})
        else:
            evidence.append("aws_managed_only=True")

    if constraints:
        status = "unsupported"
    elif unresolved:
        status = "unresolved"
    elif evidence:
        status = "supported"
    else:
        status = "unresolved"

    return {
        "candidate": candidate["name"],
        "role": role,
        "status": status,
        "evidence": evidence,
        "constraints": constraints,
        "unresolved": sorted(set(unresolved)),
        "capabilities": {
            "managed": candidate["managed"],
            "stateful": candidate["stateful"],
            "for_each_batch": candidate["for_each_batch"],
            "output_modes": candidate["output_modes"],
            "sources": candidate["sources"],
        },
    }


def analyze_streaming_architecture_path(path: str | Path) -> dict[str, Any]:
    raw = _load_input(path)
    requirements, unresolved = _declared_requirements(raw)
    assumptions, assumption_unresolved = _assumptions(raw)
    unresolved.extend(assumption_unresolved)
    matrix = [_evaluate_candidate(candidate, requirements) for candidate in CANDIDATES]
    supported = [item["candidate"] for item in matrix if item["status"] == "supported"]
    decision_status = "selected" if len(supported) == 1 else "unresolved"
    selected = supported[0] if len(supported) == 1 else None
    if len(supported) == 0:
        decision_reason = "nenhum candidato comprovadamente viavel por constraints declaradas"
    elif len(supported) > 1:
        decision_reason = "mais de um candidato permanece viavel; nao ha desempate factual"
    else:
        decision_reason = "exatamente um candidato permaneceu apos eliminacao por constraints"

    for item in matrix:
        if item["status"] == "unresolved":
            unresolved.extend(f"{item['candidate']}:{reason}" for reason in item["unresolved"])

    payload = {
        "schema_version": 1,
        "engine": ENGINE_VERSION,
        "input_sha256": _sha256(raw),
        "workload_profile": {
            "requirements": requirements,
            "assumptions": assumptions,
            "requirement_facts": _requirement_facts(requirements),
        },
        "candidate_matrix": matrix,
        "constraint_elimination": [
            {
                "candidate": item["candidate"],
                "status": item["status"],
                "constraints": item["constraints"],
            }
            for item in matrix
        ],
        "decision": {
            "status": decision_status,
            "selected": selected,
            "viable_candidates": supported,
            "reason": decision_reason,
        },
        "adr": {
            "status": decision_status,
            "context": "Escolha de plataforma para workload streaming baseada em requisitos declarados.",
            "requirements": requirements,
            "assumptions": assumptions,
            "observed_facts": _requirement_facts(requirements),
            "chosen_architecture": selected,
            "alternatives": [item["candidate"] for item in matrix if item["candidate"] != selected],
            "tradeoffs": "Nao há tradeoff resolvido quando mais de um candidato permanece viavel.",
            "risks": [
                "Premissas nao sao evidencias de capacidade.",
                "A matriz nao mede latencia, throughput, custo ou disponibilidade.",
            ],
            "validation": [
                "Validar runtime, contrato, replay, SLO e custo com artefatos do ambiente.",
            ],
            "rollback": "Reabrir decisao, preservar input e substituir somente requisitos comprovados.",
        },
        "unresolved": sorted(set(unresolved)),
    }
    return payload


def analyze_streaming_architecture(path: str | Path) -> dict[str, Any]:
    """Public entry point used by the CLI."""
    return analyze_streaming_architecture_path(path)


__all__ = [
    "CANDIDATES",
    "ENGINE_VERSION",
    "analyze_streaming_architecture",
    "analyze_streaming_architecture_path",
]
