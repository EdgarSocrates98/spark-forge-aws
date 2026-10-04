from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.fusion import fuse
from sparkforge.facts.streaming_glue_cross import (
    EMITTED_KINDS,
    build_streaming_glue_cross_artifact,
)
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_glue_cross_artifact"


def _fact(kind: str, *, attrs=None, measures=None, file="artifact.json", symbol="", line=1):
    return Fact(
        kind=kind,
        subject={
            "type": "source_location",
            "file": file,
            "line": line,
            "col": 0,
            "symbol": symbol,
            "snippet": "",
        },
        attrs=attrs or {},
        measures=measures or {},
        provenance={
            "artifact": file,
            "artifact_sha256": "a" * 64,
            "extractor": "test@0.1.0",
        },
    )


def _effective(name="rtm-valid", *, version="6.0", language="SCALA", workers=4):
    return _fact(
        "glue.streaming.job",
        file="job.json",
        symbol=name,
        attrs={
            "name": name,
            "mode": "REAL_TIME",
            "glue_version": version,
            "language": language,
        },
        measures={"worker_count": workers},
    )


def _terraform(
    name="rtm-valid",
    *,
    version="6.0",
    rtm="true",
    language="scala",
    workers=4,
    literal_name=True,
):
    symbol = "aws_glue_job.rtm"
    resource = _fact(
        "tf.resource",
        file="main.tf",
        symbol=symbol,
        attrs={"resource_type": "aws_glue_job", "resource_name": "rtm"},
        measures={"attribute_count": 5},
        line=2,
    )
    attrs = [
        _fact(
            "tf.attribute",
            file="main.tf",
            symbol=symbol,
            attrs={
                "key": "name",
                "value": name,
                "literal": literal_name,
                "present": True,
                "block": "root",
            },
            line=3,
        ),
        _fact(
            "tf.attribute",
            file="main.tf",
            symbol=symbol,
            attrs={
                "key": "glue_version",
                "value": version,
                "literal": True,
                "present": True,
                "block": "root",
            },
            line=4,
        ),
    ]
    if workers is not None:
        attrs.append(
            _fact(
                "tf.attribute",
                file="main.tf",
                symbol=symbol,
                attrs={
                    "key": "number_of_workers",
                    "value": str(workers),
                    "literal": True,
                    "present": True,
                    "block": "root",
                },
                measures={"value": workers},
                line=5,
            )
        )
    attrs.extend(
        [
            _fact(
                "tf.attribute",
                file="main.tf",
                symbol=symbol,
                attrs={
                    "key": "--enable-real-time-mode",
                    "value": rtm,
                    "literal": True,
                    "present": True,
                    "block": "default_arguments",
                },
                line=6,
            ),
            _fact(
                "tf.attribute",
                file="main.tf",
                symbol=symbol,
                attrs={
                    "key": "--job-language",
                    "value": language,
                    "literal": True,
                    "present": True,
                    "block": "default_arguments",
                },
                line=7,
            ),
        ]
    )
    return [resource, *attrs]


def _link(facts):
    return [
        fact
        for fact in build_streaming_glue_cross_artifact(facts)
        if fact.kind == "glue.streaming.terraform_link"
    ]


def test_matches_effective_glue_job_to_terraform_resource():
    links = _link([_effective(), *_terraform()])
    assert len(links) == 1
    link = links[0]
    assert link.attrs["comparison_status"] == "consistent"
    assert link.attrs["job_name"] == "rtm-valid"
    assert link.attrs["terraform_resource"] == "aws_glue_job.rtm"
    assert link.measures["comparison_count"] == 4
    assert link.measures["divergence_count"] == 0
    assert len(link.attrs["source_fact_ids"]) == 6
    validate_fact(link.to_dict())


def test_reports_drift_and_unresolved_fields_without_inference():
    drift = _link(
        [
            _effective(),
            *_terraform(version="5.0", rtm="false", language="python", workers=2),
        ]
    )[0]
    assert drift.attrs["comparison_status"] == "divergent"
    assert drift.measures["divergence_count"] == 4
    assert set(drift.attrs["drifts"]) == {"glue_version", "rtm_enabled", "language", "worker_count"}

    unresolved = _link([_effective(), *_terraform(workers=4)])[0]
    assert unresolved.attrs["comparison_status"] == "consistent"

    missing_capacity = _link(
        [
            _effective(),
            *_terraform(workers=None),
            _fact(
                "tf.unresolved",
                file="main.tf",
                symbol="aws_glue_job.rtm",
                attrs={"reason": "interpolation", "key": "number_of_workers", "block": "root"},
                line=8,
            ),
        ]
    )[0]
    assert "worker_count" in missing_capacity.attrs["unresolved_fields"]
    assert missing_capacity.attrs["comparison_status"] == "unresolved"


def test_cross_artifact_rules_are_evidence_backed():
    drift = fuse(
        [_effective(), *_terraform(version="5.0", rtm="false", language="python", workers=2)]
    )
    findings = judge(drift, load_catalog(), {})
    assert "SF-GLUESTREAM-004" in {finding.rule_id for finding in findings}
    assert all(finding.evidence for finding in findings)

    unresolved = fuse([_effective(), *_terraform(literal_name=False)])
    findings = judge(unresolved, load_catalog(), {})
    assert "SF-GLUESTREAM-005" in {finding.rule_id for finding in findings}
    assert all(finding.evidence for finding in findings)


def test_fuse_cross_artifact_is_guarded_and_idempotent():
    base = [_fact("streaming.query", attrs={"query_name": "orders"})]
    assert not [fact for fact in fuse(base) if fact.kind in EMITTED_KINDS]

    once = fuse([_effective(), *_terraform()])
    twice = fuse(once)
    def as_dicts(facts):
        return sorted((fact.to_dict() for fact in facts), key=lambda item: item["id"])

    assert as_dicts(once) == as_dicts(twice)


def _run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    inputs: list[Fact] = []
    for path in sorted((directory / "input").iterdir()):
        inputs.extend(
            Fact(
                kind=item["kind"],
                subject=item["subject"],
                measures=item.get("measures") or {},
                attrs=item.get("attrs") or {},
                provenance=item.get("provenance") or {},
                schema_version=item.get("schema_version", 1),
            )
            for item in json.loads(path.read_text(encoding="utf-8"))
        )
    facts = sort_facts(fuse(inputs))
    findings = judge(facts, load_catalog(), {})
    return meta, facts, findings


def test_fixture_goldens_cover_match_drift_and_unresolved():
    required = {"consistent", "drift", "unresolved"}
    assert {path.name for path in FIXTURES.iterdir() if path.is_dir()} == required
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta, facts, findings = _run_fixture(directory)
        expected_facts = json.loads(
            (directory / "expected" / "facts.json").read_text(encoding="utf-8")
        )
        expected_findings = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [fact.to_dict() for fact in facts] == expected_facts
        assert [finding.to_dict() for finding in findings] == expected_findings
        assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())


@pytest.mark.parametrize("directory", sorted(FIXTURES.glob("*/")), ids=lambda path: path.name)
def test_fixture_extraction_is_deterministic(directory: Path):
    first = _run_fixture(directory)[1]
    second = _run_fixture(directory)[1]
    assert [fact.to_dict() for fact in first] == [fact.to_dict() for fact in second]
