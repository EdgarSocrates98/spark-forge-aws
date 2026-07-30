import pytest

from sparkforge.findings.models import SEVERITY_ORDER, Fact, Finding, sort_facts, sort_findings


def make_fact(**over):
    base = dict(
        kind="pyspark.partitioning",
        subject={"type": "source_location", "file": "lib/loader.py", "line": 142, "col": 8},
        measures={"target_count": 1},
        attrs={"method": "coalesce", "literal_arg": True},
        provenance={"artifact": "artifacts/src/lib/loader.py", "extractor": "pyspark_ast@0.1.0"},
    )
    base.update(over)
    return Fact(**base)


class TestFactId:
    def test_id_is_stable_across_instances(self):
        assert make_fact().id == make_fact().id

    def test_id_has_expected_shape(self):
        fid = make_fact().id
        assert fid.startswith("f_")
        assert len(fid) == 8

    def test_id_changes_with_kind(self):
        assert make_fact().id != make_fact(kind="pyspark.action").id

    def test_id_changes_with_subject(self):
        other = {"type": "source_location", "file": "lib/loader.py", "line": 999, "col": 8}
        assert make_fact().id != make_fact(subject=other).id

    def test_id_changes_with_measures(self):
        assert make_fact().id != make_fact(measures={"target_count": 2}).id

    def test_id_ignores_provenance(self):
        """Provenance records where the fact came from, not what it asserts."""
        assert make_fact().id == make_fact(provenance={"artifact": "other", "extractor": "x@9"}).id

    def test_id_ignores_key_order_in_subject(self):
        reordered = {"col": 8, "line": 142, "file": "lib/loader.py", "type": "source_location"}
        assert make_fact().id == make_fact(subject=reordered).id


class TestFactSerialization:
    def test_to_dict_includes_id_and_schema_version(self):
        data = make_fact().to_dict()
        assert data["id"] == make_fact().id
        assert data["schema_version"] == 1
        assert data["kind"] == "pyspark.partitioning"

    def test_sort_facts_is_deterministic(self):
        a = make_fact(kind="pyspark.action")
        b = make_fact(kind="pyspark.partitioning")
        assert [f.kind for f in sort_facts([b, a])] == ["pyspark.action", "pyspark.partitioning"]


class TestFinding:
    def test_evidence_must_not_be_empty(self):
        with pytest.raises(ValueError, match="evidence"):
            Finding(
                rule_id="SF-PY-005",
                title="coalesce(1)",
                severity="P0",
                confidence="high",
                status="structural",
                subject={"type": "source_location", "file": "a.py", "line": 1},
                evidence=[],
            )

    def test_severity_must_be_known(self):
        with pytest.raises(ValueError, match="severity"):
            Finding(
                rule_id="SF-PY-005",
                title="x",
                severity="CRITICAL",
                confidence="high",
                status="structural",
                subject={"type": "source_location"},
                evidence=["f_abc123"],
            )

    def test_status_must_be_known(self):
        with pytest.raises(ValueError, match="status"):
            Finding(
                rule_id="SF-PY-005",
                title="x",
                severity="P0",
                confidence="high",
                status="probable",
                subject={"type": "source_location"},
                evidence=["f_abc123"],
            )

    def test_sort_findings_orders_by_severity_then_rule_id(self):
        def mk(rule_id, severity):
            return Finding(
                rule_id=rule_id,
                title="t",
                severity=severity,
                confidence="high",
                status="structural",
                subject={"type": "source_location", "file": "a.py", "line": 1},
                evidence=["f_abc123"],
            )

        items = [mk("SF-PY-009", "P2"), mk("SF-PY-005", "P0"), mk("SF-PY-002", "P2")]
        ordered = [(f.severity, f.rule_id) for f in sort_findings(items)]
        assert ordered == [("P0", "SF-PY-005"), ("P2", "SF-PY-002"), ("P2", "SF-PY-009")]

    def test_severity_order_covers_p0_to_p4(self):
        assert SEVERITY_ORDER == ("P0", "P1", "P2", "P3", "P4")
