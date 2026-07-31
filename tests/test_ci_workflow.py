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


REFRESH = ROOT / ".github" / "workflows" / "refresh-knowledge.yml"


def _load_refresh():
    return yaml.safe_load(REFRESH.read_text(encoding="utf-8"))


def _refresh_runs() -> list[str]:
    doc = _load_refresh()
    runs: list[str] = []
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if step.get("run"):
                runs.append(step["run"])
    return runs


class TestRefreshKnowledgeWorkflow:
    """`refresh_knowledge` e o unico workflow que acessa a rede externa e o
    unico que escreve no repositorio. As duas coisas exigem guarda."""

    def test_file_exists_and_is_valid_yaml(self):
        assert REFRESH.is_file()
        assert _load_refresh() is not None

    def test_is_manual_or_scheduled_but_never_runs_on_push_or_pr(self):
        """Rodar em push faria toda PR depender de rede externa e do humor de
        docs.aws.amazon.com. O resultado deste workflow nao e um veredito sobre
        o commit; e tarefa de leitura para uma pessoa."""
        doc = _load_refresh()
        triggers = doc.get("on", doc.get(True))
        assert "workflow_dispatch" in triggers
        assert "schedule" in triggers
        assert "push" not in triggers
        assert "pull_request" not in triggers

    def test_never_commits_to_main(self):
        """A secao 12.3 da spec da Fase 0 e explicita: refresh_knowledge nunca
        commita sozinho, abre PR. Um commit direto em main faria conhecimento
        entrar por scraper, que e o oposto do que o catalogo garante."""
        for run in _refresh_runs():
            assert "push origin main" not in run
            assert "push -u origin main" not in run
            assert "checkout main" not in run

    def test_the_only_commit_lands_on_a_new_branch_that_becomes_a_pr(self):
        joined = "\n".join(_refresh_runs())
        assert "git checkout -b" in joined
        assert "gh pr create" in joined

    def test_only_the_lock_is_staged(self):
        """`git add` restrito ao lock. Um `git add -A` aqui varreria para dentro
        do PR qualquer arquivo que o passo anterior tenha deixado no working
        tree -- inclusive o proprio relatorio."""
        joined = "\n".join(_refresh_runs())
        assert "git add knowledge/sources.lock.json" in joined
        assert "git add -A" not in joined
        assert "git add ." not in joined
