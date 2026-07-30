import hashlib

from sparkforge.case.resume import HANDOFF_SECTIONS, render_handoff, resume
from sparkforge.case.store import add_hypothesis, new_case, set_phase
from sparkforge.collect.base import ArtifactEntry, register_artifact

RUNTIME = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def rich_case():
    case = set_phase(new_case("sf-a", "2026-07-29T14:02:11Z", RUNTIME), "diagnosis")
    case = add_hypothesis(case, "loop recomputa DAG", "N jobs identicos", "materializar antes")
    case["facts_index"] = {
        "path": ".sparkforge/facts.json", "count": 412, "by_kind": {"pyspark.loop": 2}
    }
    case["findings_index"] = {
        "path": ".sparkforge/findings.json", "count": 3, "by_severity": {"P0": 1, "P2": 2}
    }
    case["artifacts"] = [
        {
            "kind": "event_log",
            "path": ".sparkforge/artifacts/eventlog/jr_abc.json",
            "sha256": "a" * 64,
            "source": "s3://bucket/spark-event-logs/jr_abc",
            "collect_command": "sparkforge collect eventlog --job-run jr_abc",
            "present": False,
        }
    ]
    return case


FINDINGS = [
    {"rule_id": "SF-PY-004", "severity": "P0", "title": "Action em loop",
     "subject": {"file": "lib/loader.py", "line": 88}},
    {"rule_id": "SF-PY-008", "severity": "P2", "title": "cache sem unpersist",
     "subject": {"file": "lib/loader.py", "line": 12}},
]


class TestResumePayload:
    def test_reports_phase_and_runtime(self):
        payload = resume(rich_case(), FINDINGS)
        assert payload["phase"] == "diagnosis"
        assert payload["runtime"]["glue"] == "5.0"

    def test_reports_baseline_absent_explicitly(self):
        assert resume(rich_case(), FINDINGS)["baseline"] == "ausente"

    def test_top_findings_are_ordered_by_severity(self):
        payload = resume(rich_case(), FINDINGS)
        assert [f["rule_id"] for f in payload["top_findings"]] == ["SF-PY-004", "SF-PY-008"]

    def test_open_hypotheses_carry_their_experiment(self):
        assert resume(rich_case(), FINDINGS)["open_hypotheses"][0]["experiment"] == (
            "materializar antes"
        )

    def test_missing_artifacts_carry_the_collect_command(self):
        payload = resume(rich_case(), FINDINGS)
        assert payload["missing_artifacts"][0]["collect_command"] == (
            "sparkforge collect eventlog --job-run jr_abc"
        )

    def test_next_step_is_included(self):
        assert resume(rich_case(), FINDINGS)["next_step"]["recommended_skill"]

    def test_coverage_reports_unresolved_count(self):
        assert resume(rich_case(), FINDINGS, unresolved_count=7)["coverage"]["unresolved"] == 7

    def test_payload_is_deterministic(self):
        assert resume(rich_case(), FINDINGS) == resume(rich_case(), list(reversed(FINDINGS)))


class TestHandoffMarkdown:
    def test_has_the_ten_declared_sections_in_order(self):
        assert len(HANDOFF_SECTIONS) == 10
        text = render_handoff(resume(rich_case(), FINDINGS))
        positions = [text.index("## " + s) for s in HANDOFF_SECTIONS]
        assert positions == sorted(positions)

    def test_renders_findings_with_file_and_line(self):
        text = render_handoff(resume(rich_case(), FINDINGS))
        assert "lib/loader.py:88" in text
        assert "SF-PY-004" in text

    def test_renders_collect_command_for_missing_artifact(self):
        assert "sparkforge collect eventlog --job-run jr_abc" in render_handoff(
            resume(rich_case(), FINDINGS)
        )

    def test_states_baseline_absent(self):
        assert "ausente" in render_handoff(resume(rich_case(), FINDINGS))

    def test_is_deterministic(self):
        payload = resume(rich_case(), FINDINGS)
        assert render_handoff(payload) == render_handoff(payload)


class TestRootConsultsTheManifest:
    """Sem `root`, resume() confia so na flag `present` do case (comportamento
    original). Com `root`, o manifesto de sparkforge.collect e a fonte de
    verdade por artefato -- ele reflete o disco agora, o case pode estar
    desatualizado."""

    ARTIFACT_PATH = ".sparkforge/artifacts/eventlog/jr_abc.json"

    def test_without_root_the_stale_case_flag_is_authoritative(self):
        # rich_case() grava present=False; sem root, resume nao tem como
        # saber que isso mudou.
        assert resume(rich_case(), FINDINGS)["missing_artifacts"]

    def test_with_root_a_manifest_confirmed_artifact_is_no_longer_missing(self, tmp_path):
        content = b"fake spark event log content"
        digest = hashlib.sha256(content).hexdigest()
        target = tmp_path / self.ARTIFACT_PATH
        target.parent.mkdir(parents=True)
        target.write_bytes(content)

        register_artifact(
            ArtifactEntry(
                kind="event_log",
                path=self.ARTIFACT_PATH,
                sha256=digest,
                source="s3://bucket/spark-event-logs/jr_abc",
                collect_command="sparkforge collect eventlog --job-run jr_abc",
                collected_at="2026-07-30T00:00:00Z",
            ),
            tmp_path,
        )

        payload = resume(rich_case(), FINDINGS, root=tmp_path)
        assert payload["missing_artifacts"] == []

    def test_with_root_an_artifact_absent_on_disk_stays_missing(self, tmp_path):
        # Nada registrado no manifesto em tmp_path: o artefato do case
        # continua ausente segundo a checagem por manifesto.
        payload = resume(rich_case(), FINDINGS, root=tmp_path)
        assert payload["missing_artifacts"][0]["path"] == self.ARTIFACT_PATH
