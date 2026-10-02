from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog


def _fact(kind: str, *, attrs=None, measures=None, file="streaming.jsonl"):
    return Fact(
        kind=kind,
        subject={"type": "source_location", "file": file, "line": 1, "col": 0},
        attrs=attrs or {},
        measures=measures or {},
        provenance={"artifact": file, "artifact_sha256": "a" * 64, "extractor": "test@0.1.0"},
    )


def test_streaming_rules_require_runtime_and_sufficient_evidence():
    rules = [rule for rule in load_catalog() if rule["id"].startswith("SF-STREAM-")]
    assert {rule["id"] for rule in rules} >= {"SF-STREAM-001", "SF-STREAM-002", "SF-STREAM-003"}

    query = _fact("streaming.query", attrs={"checkpoint_configured": False})
    series = _fact(
        "streaming.progress.series",
        measures={
            "observation_count": 2,
        },
        attrs={"all_processed_below_input": True, "state_growth_observed": True},
    )
    runtime = _fact(
        "env.runtime_signal",
        measures={"distinct_versions": 1},
        attrs={"observed": {"spark": ["3.5.6"]}},
    )

    findings, skipped = judge(
        [query, series, runtime], rules, {"spark": "3.5.6"}, return_skipped=True
    )
    assert {finding.rule_id for finding in findings} >= {
        "SF-STREAM-001",
        "SF-STREAM-002",
        "SF-STREAM-003",
    }
    assert all(finding.evidence for finding in findings)
    assert not [item for item in skipped if item["rule_id"] in {finding.rule_id for finding in findings}]

    no_runtime = judge([query, series], rules, {"spark": "3.5.6"})
    assert not no_runtime

    one_observation = _fact(
        "streaming.progress.series",
        measures={"observation_count": 1},
        attrs={"all_processed_below_input": True},
    )
    assert not judge([runtime, one_observation], rules, {"spark": "3.5.6"})


def test_temporal_rule_requires_paired_observations():
    rules = [rule for rule in load_catalog() if rule["id"].startswith("SF-STREAMOBS-")]
    assert "SF-STREAMOBS-002" in {rule["id"] for rule in rules}
    temporal = _fact(
        "streaming.temporal.diagnostic",
        measures={"paired_observation_count": 2},
        attrs={
            "temporal_window_complete": True,
            "all_paired_processed_below_input": True,
            "transport_backlog_observed": True,
            "causal_inference": False,
        },
    )
    runtime = _fact(
        "env.runtime_signal",
        measures={"distinct_versions": 1},
        attrs={"observed": {"spark": ["3.5.6"]}},
    )
    findings = judge([temporal, runtime], rules, {"spark": "3.5.6"})
    assert [finding for finding in findings if finding.rule_id == "SF-STREAMOBS-002"]
    assert all(finding.evidence for finding in findings)

    one_pair = _fact(
        "streaming.temporal.diagnostic",
        measures={"paired_observation_count": 1},
        attrs={
            "temporal_window_complete": True,
            "all_paired_processed_below_input": True,
            "transport_backlog_observed": True,
        },
    )
    assert not [
        finding
        for finding in judge([one_pair, runtime], rules, {"spark": "3.5.6"})
        if finding.rule_id == "SF-STREAMOBS-002"
    ]


def test_temporal_iceberg_rule_requires_pairs_and_non_append():
    rules = [rule for rule in load_catalog() if rule["id"].startswith("SF-STREAMICE-")]
    temporal = _fact(
        "streaming.iceberg.temporal",
        attrs={
            "temporal_window_complete": True,
            "non_append_observed": True,
            "causal_inference": False,
        },
        measures={"paired_observation_count": 2, "non_append_snapshot_count": 1},
    )
    findings = judge([temporal], rules, {})
    assert [finding for finding in findings if finding.rule_id == "SF-STREAMICE-002"]

    append_only = _fact(
        "streaming.iceberg.temporal",
        attrs={"temporal_window_complete": True, "non_append_observed": False},
        measures={"paired_observation_count": 2},
    )
    assert not [
        finding
        for finding in judge([append_only], rules, {})
        if finding.rule_id == "SF-STREAMICE-002"
    ]
