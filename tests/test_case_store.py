import pytest
import yaml

from sparkforge.case.store import (
    CaseError,
    add_hypothesis,
    load_case,
    new_case,
    record_skill_use,
    save_case,
    set_gate,
    set_phase,
)

RUNTIME = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


class TestNewCase:
    def test_has_required_top_level_keys(self):
        case = new_case("sf-2026-07-29-a", "2026-07-29T14:02:11Z", RUNTIME, repo="/r")
        for key in (
            "schema_version", "case_id", "created_at", "runtime", "scope", "phase",
            "artifacts", "facts_index", "findings_index", "baseline", "hypotheses",
            "gates", "skills_used", "open_questions",
        ):
            assert key in case

    def test_starts_in_intake_phase(self):
        assert new_case("c", "2026-07-29T00:00:00Z", RUNTIME)["phase"] == "intake"

    def test_gates_start_false(self):
        assert new_case("c", "2026-07-29T00:00:00Z", RUNTIME)["gates"] == {
            "baseline_captured": False,
            "dominant_bottleneck_identified": False,
            "functional_validation_defined": False,
            "flows_mapped": False,
        }

    def test_baseline_starts_null(self):
        assert new_case("c", "2026-07-29T00:00:00Z", RUNTIME)["baseline"] is None

    def test_timestamp_is_injected_never_generated(self):
        """Timestamp vem do processo, nunca do LLM, e nunca de relogio interno."""
        case = new_case("c", "2026-07-29T09:15:00Z", RUNTIME)
        assert case["created_at"] == "2026-07-29T09:15:00Z"


class TestRoundTrip:
    def test_save_then_load_is_identical(self, tmp_path):
        case = new_case("c", "2026-07-29T00:00:00Z", RUNTIME, repo=str(tmp_path))
        path = save_case(case, tmp_path)
        assert path == tmp_path / ".sparkforge" / "case.yaml"
        assert load_case(tmp_path) == case

    def test_saved_yaml_is_deterministic(self, tmp_path):
        case = new_case("c", "2026-07-29T00:00:00Z", RUNTIME)
        first = save_case(case, tmp_path).read_text(encoding="utf-8")
        second = save_case(case, tmp_path).read_text(encoding="utf-8")
        assert first == second

    def test_load_missing_case_raises_with_actionable_message(self, tmp_path):
        with pytest.raises(CaseError, match="sparkforge case open"):
            load_case(tmp_path)

    def test_load_rejects_unknown_schema_version(self, tmp_path):
        target = tmp_path / ".sparkforge"
        target.mkdir()
        (target / "case.yaml").write_text(
            yaml.safe_dump({"schema_version": 99, "case_id": "c"}), encoding="utf-8"
        )
        with pytest.raises(CaseError, match="schema_version"):
            load_case(tmp_path)


class TestMutators:
    def _case(self):
        return new_case("c", "2026-07-29T00:00:00Z", RUNTIME)

    def test_set_phase_accepts_known_phase(self):
        assert set_phase(self._case(), "diagnosis")["phase"] == "diagnosis"

    def test_set_phase_rejects_unknown_phase(self):
        with pytest.raises(CaseError, match="fase"):
            set_phase(self._case(), "vibes")

    def test_set_gate_flips_value(self):
        assert set_gate(self._case(), "baseline_captured", True)["gates"]["baseline_captured"]

    def test_set_gate_rejects_unknown_gate(self):
        with pytest.raises(CaseError, match="gate"):
            set_gate(self._case(), "vibes_ok", True)

    def test_add_hypothesis_assigns_sequential_id(self):
        case = add_hypothesis(
            self._case(), "loop recomputa DAG", "N jobs identicos", "materializar"
        )
        case = add_hypothesis(case, "skew na chave nula", "max/p50 cai", "separar nulls")
        assert [h["id"] for h in case["hypotheses"]] == ["h1", "h2"]

    def test_new_hypothesis_starts_open(self):
        assert add_hypothesis(self._case(), "s", "p", "e")["hypotheses"][0]["status"] == "open"

    def test_record_skill_use_appends_with_outcome(self):
        case = record_skill_use(
            self._case(), "diagnose-data-skew", "2026-07-29T10:00:00Z", "skew confirmado"
        )
        entry = case["skills_used"][0]
        assert entry["skill"] == "diagnose-data-skew"
        assert entry["at"] == "2026-07-29T10:00:00Z"
        assert entry["outcome"] == "skew confirmado"

    def test_mutators_do_not_alter_the_input(self):
        original = self._case()
        set_phase(original, "diagnosis")
        assert original["phase"] == "intake"
