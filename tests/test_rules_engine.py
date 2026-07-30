from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge

GLUE_50 = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def rule(**over):
    base = {
        "id": "SF-T-001",
        "category": "test",
        "title": "titulo",
        "requires_facts": ["k"],
        "when": {"all": [{"fact": "k", "where": {"attrs.flag": True}}]},
        "status": "structural",
        "severity_default": "P2",
        "runtime_scope": {"glue": "*"},
        "sources": [{"origin": "field-heuristic"}],
        "catalog_version": 1,
        "explanation": "porque custa",
        "proposed_change": ["mudar"],
        "risks": ["risco"],
        "validation": ["contagem total"],
        "rollback": ["reverter"],
    }
    base.update(over)
    return base


def fact(**over):
    base = {
        "kind": "k",
        "subject": {"type": "source_location", "file": "a.py", "line": 1},
        "measures": {},
        "attrs": {"flag": True},
    }
    base.update(over)
    return Fact(**base)


class TestWhereMatching:
    def test_matching_where_produces_finding(self):
        found = judge([fact()], [rule()], GLUE_50)
        assert [f.rule_id for f in found] == ["SF-T-001"]

    def test_non_matching_where_produces_nothing(self):
        assert judge([fact(attrs={"flag": False})], [rule()], GLUE_50) == []

    def test_finding_evidence_points_at_the_fact(self):
        the_fact = fact()
        found = judge([the_fact], [rule()], GLUE_50)
        assert found[0].evidence == [the_fact.id]

    def test_finding_inherits_subject_from_primary_fact(self):
        found = judge([fact()], [rule()], GLUE_50)
        assert found[0].subject == {"type": "source_location", "file": "a.py", "line": 1}

    def test_finding_carries_rule_narrative_fields(self):
        found = judge([fact()], [rule()], GLUE_50)[0]
        assert found.explanation == "porque custa"
        assert found.proposed_change == ["mudar"]
        assert found.validation == ["contagem total"]
        assert found.rollback == ["reverter"]
        assert found.sources == [{"origin": "field-heuristic"}]


class TestRequiresFacts:
    def test_rule_is_skipped_when_required_kind_absent(self):
        """Kind nao extraido nao gera falso negativo silencioso: a regra e reportada
        como skipped, nao avaliada."""
        found, skipped = judge([], [rule()], GLUE_50, return_skipped=True)
        assert found == []
        assert skipped[0]["rule_id"] == "SF-T-001"
        assert skipped[0]["reason"] == "requires_facts"


class TestVersionScope:
    def test_out_of_scope_rule_is_skipped_with_reason(self):
        scoped = rule(runtime_scope={"iceberg": ">=1.10.0"})
        found, skipped = judge([fact()], [scoped], GLUE_50, return_skipped=True)
        assert found == []
        assert skipped[0]["reason"] == "runtime_scope"
        assert skipped[0]["scope"] == {"iceberg": ">=1.10.0"}

    def test_in_scope_rule_fires(self):
        scoped = rule(runtime_scope={"iceberg": ">=1.7.0"})
        assert len(judge([fact()], [scoped], GLUE_50)) == 1


class TestExprAndThreshold:
    def test_expr_with_threshold_fires_above_limit(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        assert len(judge([fact(measures={"n": 12})], [r], GLUE_50)) == 1

    def test_expr_with_threshold_does_not_fire_below_limit(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        assert judge([fact(measures={"n": 9})], [r], GLUE_50) == []

    def test_threshold_and_measured_appear_on_the_finding(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        found = judge([fact(measures={"n": 12})], [r], GLUE_50)[0]
        assert found.threshold == {"n": 10}
        assert found.measured == {"n": 12}


class TestSeverityBy:
    def _rule(self):
        return rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 3},
            severity_by=[
                {"when": "measures.n >= 10", "severity": "P0"},
                {"when": "measures.n >= 3", "severity": "P2"},
            ],
        )

    def test_first_matching_branch_wins(self):
        assert judge([fact(measures={"n": 12})], [self._rule()], GLUE_50)[0].severity == "P0"

    def test_second_branch_when_first_does_not_match(self):
        assert judge([fact(measures={"n": 5})], [self._rule()], GLUE_50)[0].severity == "P2"


class TestAnyAndAbsent:
    def test_any_group_fires_on_one_match(self):
        r = rule(
            when={
                "any": [
                    {"fact": "k", "where": {"attrs.flag": False}},
                    {"fact": "k", "where": {"attrs.flag": True}},
                ]
            }
        )
        assert len(judge([fact()], [r], GLUE_50)) == 1

    def test_absent_condition_fires_when_kind_missing(self):
        r = rule(
            requires_facts=["k"],
            when={"all": [{"fact": "k"}, {"absent": "other.kind"}]},
        )
        assert len(judge([fact()], [r], GLUE_50)) == 1

    def test_absent_condition_blocks_when_kind_present(self):
        r = rule(
            requires_facts=["k"],
            when={"all": [{"fact": "k"}, {"absent": "other.kind"}]},
        )
        facts = [fact(), fact(kind="other.kind")]
        assert judge(facts, [r], GLUE_50) == []


class TestDeterminism:
    def test_findings_are_sorted_and_stable(self):
        r_a = rule(id="SF-T-009", severity_default="P2")
        r_b = rule(id="SF-T-002", severity_default="P0")
        first = [f.to_dict() for f in judge([fact()], [r_a, r_b], GLUE_50)]
        second = [f.to_dict() for f in judge([fact()], [r_b, r_a], GLUE_50)]
        assert first == second
        assert [f["rule_id"] for f in first] == ["SF-T-002", "SF-T-009"]


class TestVerticalSliceEndToEnd:
    """A prova da Fase 0: codigo-fonte entra, Finding ancorado sai."""

    def test_coalesce_one_yields_sf_py_005_at_the_right_line(self):
        from sparkforge.rules.loader import load_catalog

        source = 'df.select("a").coalesce(1).write.parquet("s3://b/p")\n'
        facts = extract_source(source, "lib/loader.py")
        catalog = [r for r in load_catalog() if r["id"] == "SF-PY-005"]
        assert catalog, "SF-PY-005 ausente do catalogo"

        found = judge(facts, catalog, GLUE_50)
        assert len(found) == 1
        finding = found[0]
        assert finding.rule_id == "SF-PY-005"
        assert finding.severity == "P0"
        assert finding.status == "structural"
        assert finding.subject["file"] == "lib/loader.py"
        assert finding.subject["line"] == 1
        assert len(finding.evidence) == 1
        assert finding.evidence[0].startswith("f_")

    def test_repartition_200_does_not_trigger_coalesce_rule(self):
        from sparkforge.rules.loader import load_catalog

        facts = extract_source("df.repartition(200)\n", "lib/loader.py")
        catalog = [r for r in load_catalog() if r["id"] == "SF-PY-005"]
        assert judge(facts, catalog, GLUE_50) == []
