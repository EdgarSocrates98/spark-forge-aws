from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _load():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _all_step_runs() -> list[str]:
    doc = _load()
    runs: list[str] = []
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            run = step.get("run")
            if run:
                runs.append(run)
    return runs


class TestWorkflowExists:
    def test_file_exists(self):
        assert WORKFLOW.is_file()

    def test_is_valid_yaml(self):
        assert _load() is not None


class TestMatrix:
    def test_tests_both_3_10_and_3_11(self):
        doc = _load()
        versions = doc["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert "3.10" in versions
        assert "3.11" in versions


class TestSteps:
    def test_runs_pytest(self):
        assert any("python -m pytest" in run for run in _all_step_runs())

    def test_runs_sync_skills_check(self):
        assert any("sync_skills.py --check" in run for run in _all_step_runs())

    def test_runs_check_evals(self):
        assert any("check_evals.py" in run for run in _all_step_runs())

    def test_runs_ruff(self):
        assert any("ruff check" in run for run in _all_step_runs())


class TestTriggers:
    def test_includes_workflow_dispatch(self):
        doc = _load()
        # YAML 1.1 treats a bare `on:` key as boolean True when parsed by
        # PyYAML's safe_load; guard against both to avoid a KeyError that
        # looks unrelated to the actual assertion.
        triggers = doc.get("on", doc.get(True))
        assert "workflow_dispatch" in triggers


class TestNoAutoCommit:
    def test_no_step_runs_git_commit(self):
        assert not any("git commit" in run for run in _all_step_runs())
