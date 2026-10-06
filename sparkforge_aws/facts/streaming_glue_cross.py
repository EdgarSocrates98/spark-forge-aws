"""Composição offline entre definição efetiva Glue Streaming e Terraform.

Os extratores de Glue e Terraform observam fontes diferentes. Este módulo não
lê arquivos: recebe Facts já extraídos, casa somente por ``name`` literal único
e publica um resumo reauditable com os ids das fontes. Valor ausente ou
interpolado continua ``unresolved``; resource name não substitui identidade do
job.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge_aws.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_glue_cross@0.1.0"
SOURCE_KINDS = frozenset({"glue.streaming.job", "tf.resource", "tf.attribute", "tf.unresolved"})
EMITTED_KINDS = frozenset({"glue.streaming.terraform_link", "glue.streaming.cross.unresolved"})

_COMPARISON_FIELDS = (
    "glue_version",
    "rtm_enabled",
    "language",
    "worker_count",
)


def _subject(symbol: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": "<composition>",
        "line": 0,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _provenance(facts: Sequence[Fact]) -> dict[str, Any]:
    return {
        "artifact": "<composition>",
        "artifacts": sorted(
            {
                str(fact.provenance.get("artifact"))
                for fact in facts
                if fact.provenance.get("artifact")
            }
        ),
        "extractor": EXTRACTOR_ID,
    }


def _source_ids(facts: Sequence[Fact]) -> list[str]:
    return sorted({fact.id for fact in facts})


def _tf_symbol(fact: Fact) -> str:
    return str((fact.subject or {}).get("symbol") or "")


def _is_literal(fact: Fact) -> bool:
    attrs = fact.attrs or {}
    return attrs.get("literal") is True and attrs.get("present") is True


def _attributes_by_symbol(facts: Sequence[Fact]) -> dict[str, list[Fact]]:
    grouped: dict[str, list[Fact]] = {}
    for fact in facts:
        if fact.kind not in {"tf.attribute", "tf.unresolved"}:
            continue
        symbol = _tf_symbol(fact)
        if symbol:
            grouped.setdefault(symbol, []).append(fact)
    return grouped


def _resource_facts(facts: Sequence[Fact]) -> list[Fact]:
    return [
        fact
        for fact in facts
        if fact.kind == "tf.resource"
        and str((fact.attrs or {}).get("resource_type") or "") == "aws_glue_job"
    ]


def _name_attributes(attributes: Sequence[Fact]) -> list[Fact]:
    return [fact for fact in attributes if (fact.attrs or {}).get("key") == "name"]


def _unresolved(
    job: Fact,
    reason: str,
    source_facts: Sequence[Fact],
    *,
    field: str = "",
    terraform_resources: Sequence[str] = (),
) -> Fact:
    attrs: dict[str, Any] = {
        "reason": reason,
        "job_name": (job.attrs or {}).get("name") or None,
        "source_fact_ids": _source_ids(source_facts),
    }
    if field:
        attrs["field"] = field
    if terraform_resources:
        attrs["terraform_resources"] = sorted(set(terraform_resources))
    return Fact(
        kind="glue.streaming.cross.unresolved",
        subject=_subject(str((job.attrs or {}).get("name") or "<unnamed-job>")),
        attrs=attrs,
        provenance=_provenance(source_facts),
    )


def _attribute_value(attributes: Sequence[Fact], key: str, block: str | None = None) -> Fact | None:
    candidates = [
        fact
        for fact in attributes
        if fact.kind == "tf.attribute"
        and (fact.attrs or {}).get("key") == key
        and (block is None or (fact.attrs or {}).get("block") == block)
    ]
    if len(candidates) != 1:
        return None
    return candidates[0]


def _unresolved_attribute(attributes: Sequence[Fact], key: str, block: str | None = None) -> bool:
    return any(
        fact.kind == "tf.unresolved"
        and (fact.attrs or {}).get("key") == key
        and (block is None or (fact.attrs or {}).get("block") == block)
        for fact in attributes
    )


def _declared_value(
    attributes: Sequence[Fact], key: str, *, block: str | None = None
) -> tuple[Any, bool]:
    fact = _attribute_value(attributes, key, block)
    if fact is None or not _is_literal(fact):
        return None, False
    if key == "number_of_workers":
        value = (fact.measures or {}).get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value, True
        raw = (fact.attrs or {}).get("value")
        try:
            return int(raw), True
        except (TypeError, ValueError):
            return None, False
    return (fact.attrs or {}).get("value"), True


def _observed_values(job: Fact) -> dict[str, tuple[Any, bool]]:
    attrs = job.attrs or {}
    measures = job.measures or {}
    mode = str(attrs.get("mode") or "").upper()
    return {
        "glue_version": (attrs.get("glue_version"), bool(attrs.get("glue_version"))),
        "rtm_enabled": (mode == "REAL_TIME", bool(mode)),
        "language": (
            str(attrs.get("language")).upper() if attrs.get("language") is not None else None,
            attrs.get("language") is not None,
        ),
        "worker_count": (
            measures.get("worker_count"),
            isinstance(measures.get("worker_count"), (int, float))
            and not isinstance(measures.get("worker_count"), bool),
        ),
    }


def _declared_values(attributes: Sequence[Fact]) -> tuple[dict[str, tuple[Any, bool]], set[str]]:
    unresolved_fields: set[str] = set()
    values: dict[str, tuple[Any, bool]] = {}
    for field, key, block in (
        ("glue_version", "glue_version", "root"),
        ("rtm_enabled", "--enable-real-time-mode", "default_arguments"),
        ("language", "--job-language", "default_arguments"),
        ("worker_count", "number_of_workers", "root"),
    ):
        value, observed = _declared_value(attributes, key, block=block)
        if field == "rtm_enabled" and observed:
            text = str(value).strip().lower()
            if text in {"true", "false"}:
                value = text == "true"
            else:
                observed = False
        elif field == "language" and observed:
            value = str(value).upper()
        values[field] = (value, observed)
        if not observed and (
            _unresolved_attribute(attributes, key, block)
            or _attribute_value(attributes, key, block) is None
        ):
            unresolved_fields.add(field)
    return values, unresolved_fields


def _matching_resource(
    job: Fact,
    resources: Sequence[Fact],
    attributes_by_symbol: dict[str, list[Fact]],
    all_facts: Sequence[Fact],
) -> tuple[Fact | None, Fact | None]:
    job_name = str((job.attrs or {}).get("name") or "")
    if not job_name:
        return None, _unresolved(job, "effective_job_name_missing", all_facts)
    matches: list[Fact] = []
    non_literal_match = False
    for resource in resources:
        symbol = _tf_symbol(resource)
        name_facts = _name_attributes(attributes_by_symbol.get(symbol, []))
        for name_fact in name_facts:
            value = (name_fact.attrs or {}).get("value")
            if value == job_name:
                if _is_literal(name_fact):
                    matches.append(resource)
                else:
                    non_literal_match = True
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, _unresolved(
            job,
            "ambiguous_terraform_job_name",
            all_facts,
            terraform_resources=[_tf_symbol(resource) for resource in matches],
        )
    return None, _unresolved(
        job,
        "identity_not_literal" if non_literal_match else "terraform_job_name_not_found",
        all_facts,
    )


def _link(job: Fact, resource: Fact, attributes: Sequence[Fact], all_facts: Sequence[Fact]) -> Fact:
    observed = _observed_values(job)
    declared, unresolved_fields = _declared_values(attributes)
    drifts: list[str] = []
    comparison_count = 0
    divergence_count = 0
    compared_ids = [job.id, resource.id]
    for field in _COMPARISON_FIELDS:
        value, observed_present = observed[field]
        declared_value, declared_present = declared[field]
        if observed_present and declared_present:
            comparison_count += 1
            compared_ids.extend(
                fact.id
                for fact in attributes
                if fact.kind == "tf.attribute"
                and (
                    (field == "glue_version" and (fact.attrs or {}).get("key") == "glue_version")
                    or (
                        field == "rtm_enabled"
                        and (fact.attrs or {}).get("key") == "--enable-real-time-mode"
                    )
                    or (field == "language" and (fact.attrs or {}).get("key") == "--job-language")
                    or (
                        field == "worker_count"
                        and (fact.attrs or {}).get("key") == "number_of_workers"
                    )
                )
            )
            if value != declared_value:
                divergence_count += 1
                drifts.append(field)
    status = "divergent" if drifts else ("unresolved" if unresolved_fields else "consistent")
    source_ids = sorted(set(compared_ids))
    attrs: dict[str, Any] = {
        "job_name": (job.attrs or {}).get("name"),
        "terraform_resource": _tf_symbol(resource),
        "comparison_status": status,
        "drifts": sorted(drifts),
        "unresolved_fields": sorted(unresolved_fields),
        "source_fact_ids": source_ids,
    }
    return Fact(
        kind="glue.streaming.terraform_link",
        subject=_subject(f"{attrs['job_name']}->{attrs['terraform_resource']}"),
        measures={
            "comparison_count": comparison_count,
            "divergence_count": divergence_count,
            "unresolved_count": len(unresolved_fields),
        },
        attrs=attrs,
        provenance=_provenance([job, resource, *attributes]),
    )


def build_streaming_glue_cross_artifact(facts: Sequence[Fact]) -> list[Fact]:
    """Derive Glue effective→Terraform links from an existing fact pool."""
    source = [fact for fact in facts if fact.kind in SOURCE_KINDS]
    jobs = [fact for fact in source if fact.kind == "glue.streaming.job"]
    resources = _resource_facts(source)
    attributes_by_symbol = _attributes_by_symbol(source)
    if not jobs or not resources:
        return []
    derived: list[Fact] = []
    for job in jobs:
        resource, unresolved = _matching_resource(job, resources, attributes_by_symbol, source)
        if unresolved is not None:
            derived.append(unresolved)
            continue
        assert resource is not None
        attrs = attributes_by_symbol.get(_tf_symbol(resource), [])
        derived.append(_link(job, resource, attrs, source))
    unknown = {fact.kind for fact in derived} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace Glue cross-artifact: {sorted(unknown)}")
    return sort_facts(derived)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "SOURCE_KINDS",
    "build_streaming_glue_cross_artifact",
]
