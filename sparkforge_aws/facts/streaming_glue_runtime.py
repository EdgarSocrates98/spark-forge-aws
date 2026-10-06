"""Composição offline entre job Glue Streaming e runs Glue observados.

O módulo recebe Facts já extraídos e não lê arquivos, consulta AWS ou calcula
capacidade por inferência. A definição efetiva fornece a expectativa observada
no artefato; ``glue.job_run`` fornece o que o histórico terminal registrou.
Ausência de run/campo é ``unresolved``, nunca igualdade.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge_aws.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_glue_runtime@0.1.0"

SOURCE_KINDS = frozenset(
    {
        "glue.streaming.job",
        "glue.job_run",
        "glue.job_run.analyzed",
    }
)

EMITTED_KINDS = frozenset(
    {
        "glue.streaming.runtime_link",
        "glue.streaming.runtime.unresolved",
    }
)

_AXES = ("glue_version", "worker_type", "worker_count")


def _subject(job_name: str, symbol: str = "") -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": "<fusion>",
        "line": 0,
        "col": 0,
        "symbol": symbol or job_name,
        "snippet": "",
    }


def _provenance(source_fact_ids: Sequence[str]) -> dict[str, Any]:
    return {
        "extractor": EXTRACTOR_ID,
        "artifact": "<fusion>",
        "source_fact_ids": sorted(set(source_fact_ids)),
    }


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _job_name(fact: Fact) -> str | None:
    return _text((fact.attrs or {}).get("name"))


def _run_job_name(fact: Fact) -> str | None:
    return _text((fact.subject or {}).get("job_name"))


def _effective_values(fact: Fact) -> dict[str, Any | None]:
    attrs = fact.attrs or {}
    measures = fact.measures or {}
    return {
        "glue_version": _text(attrs.get("glue_version")),
        "worker_type": _text(attrs.get("worker_type")),
        "worker_count": _number(measures.get("worker_count")),
    }


def _run_values(fact: Fact) -> dict[str, Any | None]:
    attrs = fact.attrs or {}
    measures = fact.measures or {}
    return {
        "glue_version": _text(attrs.get("glue_version")),
        "worker_type": _text(attrs.get("worker_type")),
        "worker_count": _number(measures.get("number_of_workers")),
    }


def _observed_values(runs: Sequence[Fact], axis: str) -> list[Any]:
    values = {_run_values(run)[axis] for run in runs}
    return sorted((value for value in values if value is not None), key=lambda value: str(value))


def _run_id(fact: Fact) -> str:
    return (
        _text((fact.subject or {}).get("job_run_id"))
        or _text((fact.subject or {}).get("symbol"))
        or fact.id
    )


def _unresolved(
    *,
    reason: str,
    job_name: str,
    source_facts: Sequence[Fact],
    unresolved_fields: Sequence[str] = (),
    run_count: int = 0,
) -> Fact:
    source_ids = sorted({fact.id for fact in source_facts})
    return Fact(
        kind="glue.streaming.runtime.unresolved",
        subject=_subject(job_name, "unresolved"),
        measures={"run_count": run_count, "unresolved_count": len(set(unresolved_fields))},
        attrs={
            "job_name": job_name,
            "reason": reason,
            "unresolved_fields": sorted(set(unresolved_fields)),
            "source_fact_ids": source_ids,
        },
        provenance=_provenance(source_ids),
    )


def _link(job: Fact, runs: Sequence[Fact], analyzed: Sequence[Fact]) -> Fact:
    effective = _effective_values(job)
    source_facts = [job, *runs, *analyzed]
    source_ids = sorted({fact.id for fact in source_facts})
    observed = {axis: _observed_values(runs, axis) for axis in _AXES}
    drifts: list[str] = []
    unresolved_fields: list[str] = []

    for axis in _AXES:
        expected = effective[axis]
        values = observed[axis]
        if expected is None or not values:
            unresolved_fields.append(axis)
            continue
        if len(values) > 1 or values[0] != expected:
            drifts.append(axis)

    status = "unresolved" if unresolved_fields else ("divergent" if drifts else "consistent")
    states = sorted(
        {
            state
            for state in (_text((run.attrs or {}).get("state")) for run in runs)
            if state is not None
        }
    )
    attrs: dict[str, Any] = {
        "job_name": _job_name(job) or "",
        "comparison_status": status,
        "drifts": sorted(drifts),
        "unresolved_fields": sorted(unresolved_fields),
        "observed_states": states,
        "observed_run_ids": sorted({_run_id(run) for run in runs}),
        "observed_glue_versions": observed["glue_version"],
        "observed_worker_types": observed["worker_type"],
        "observed_worker_counts": observed["worker_count"],
        "source_fact_ids": source_ids,
    }
    return Fact(
        kind="glue.streaming.runtime_link",
        subject=_subject(attrs["job_name"]),
        measures={
            "run_count": len(runs),
            "comparison_count": len(_AXES),
            "divergence_count": len(drifts),
            "unresolved_count": len(unresolved_fields),
        },
        attrs=attrs,
        provenance=_provenance(source_ids),
    )


def build_streaming_glue_runtime_observation(facts: Sequence[Fact]) -> list[Fact]:
    """Correlaciona job efetivo com runs terminais por identidade literal.

    Jobs com nome ausente/duplicado, runs sem ``job_name`` e histórico sem
    fact individual produzem lacuna nomeada. A função é pura e determinística;
    retornar facts ordenados permite goldens e ``fuse`` idempotentes.
    """
    jobs = [fact for fact in facts if fact.kind == "glue.streaming.job"]
    runs = [fact for fact in facts if fact.kind == "glue.job_run"]
    analyzed = [fact for fact in facts if fact.kind == "glue.job_run.analyzed"]
    if not jobs:
        return []

    output: list[Fact] = []
    by_name: dict[str, list[Fact]] = {}
    for run in runs:
        name = _run_job_name(run)
        if name is None:
            output.append(
                _unresolved(
                    reason="run_job_name_missing",
                    job_name="",
                    source_facts=[run],
                )
            )
            continue
        by_name.setdefault(name, []).append(run)

    analyzed_by_name: dict[str, list[Fact]] = {}
    for fact in analyzed:
        name = _run_job_name(fact)
        if name is not None:
            analyzed_by_name.setdefault(name, []).append(fact)

    jobs_by_name: dict[str, list[Fact]] = {}
    for job in jobs:
        name = _job_name(job)
        if name is None:
            output.append(
                _unresolved(
                    reason="effective_job_name_missing",
                    job_name="",
                    source_facts=[job],
                    unresolved_fields=("job_name",),
                )
            )
            continue
        jobs_by_name.setdefault(name, []).append(job)

    for name, matching_jobs in sorted(jobs_by_name.items()):
        if len(matching_jobs) != 1:
            output.append(
                _unresolved(
                    reason="ambiguous_effective_job_identity",
                    job_name=name,
                    source_facts=matching_jobs,
                    unresolved_fields=("job_name",),
                )
            )
            continue

        matching_runs = by_name.get(name, [])
        matching_analyzed = analyzed_by_name.get(name, [])
        if not matching_runs:
            expected_runs = sum(
                int(fact.measures.get("runs_analyzed", 0) or 0) for fact in matching_analyzed
            )
            output.append(
                _unresolved(
                    reason="run_facts_missing" if expected_runs else "run_observation_missing",
                    job_name=name,
                    source_facts=[matching_jobs[0], *matching_analyzed],
                    unresolved_fields=_AXES,
                    run_count=expected_runs,
                )
            )
            continue

        link = _link(matching_jobs[0], matching_runs, matching_analyzed)
        output.append(link)
        if link.attrs.get("unresolved_fields"):
            output.append(
                _unresolved(
                    reason="runtime_fields_missing",
                    job_name=name,
                    source_facts=[matching_jobs[0], *matching_runs, *matching_analyzed],
                    unresolved_fields=link.attrs["unresolved_fields"],
                    run_count=len(matching_runs),
                )
            )

    return sort_facts(output)
