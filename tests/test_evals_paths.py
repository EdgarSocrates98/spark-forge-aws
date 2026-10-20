"""Resolucao das suites de evals: env -> cwd -> repositorio -> pacote.

Cobre a parte do Ciclo 12 em que `python -m sparkforge_aws.evals` nao pode
depender implicitamente do cwd: fora do checkout as suites versionadas vem de
`sparkforge_aws/evals_data/` (force-include do wheel), e um workspace do
usuario com `evals/agentic/` proprio continua vencendo.
"""
from pathlib import Path

import pytest

from sparkforge_aws.evals.paths import (
    PACKAGED_EVALS,
    EvalsError,
    suite_dir,
    suites_disponiveis,
)

REPO = Path(__file__).resolve().parents[1]


def test_checkout_suites_resolve_via_repo_root(tmp_path):
    """cwd vazio fora do repo: a raiz versionada responde."""
    assert suite_dir("debate", cwd=tmp_path) == REPO / "evals" / "agentic" / "debate"


def test_workspace_suite_wins_over_versioned(tmp_path):
    local = tmp_path / "evals" / "agentic" / "debate"
    local.mkdir(parents=True)
    assert suite_dir("debate", cwd=tmp_path) == local


def test_workspace_partial_still_sees_versioned(tmp_path):
    """Um workspace com so suites locais nao esconde as versionadas."""
    (tmp_path / "evals" / "agentic" / "minha").mkdir(parents=True)
    assert "minha" in suites_disponiveis(cwd=tmp_path)
    assert suite_dir("fase0", cwd=tmp_path) == REPO / "evals" / "agentic" / "fase0"


def test_unknown_suite_refuses(tmp_path):
    with pytest.raises(EvalsError):
        suite_dir("nao-existe", cwd=tmp_path)


def test_env_override(tmp_path, monkeypatch):
    base = tmp_path / "alt"
    (base / "agentic" / "x").mkdir(parents=True)
    monkeypatch.setenv("SPARKFORGE_AWS_EVALS", str(base))
    assert suite_dir("x", cwd=tmp_path) == base / "agentic" / "x"
    with pytest.raises(EvalsError):
        suite_dir("debate", cwd=tmp_path)


def test_env_override_missing_dir_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("SPARKFORGE_AWS_EVALS", str(tmp_path / "nada"))
    with pytest.raises(EvalsError):
        suite_dir("debate", cwd=tmp_path)


def test_wheel_path_constant_points_inside_the_package():
    """`evals_data` so existe no wheel; a constante tem que apontar para
    dentro de `sparkforge_aws/` para o fallback empacotado funcionar."""
    assert PACKAGED_EVALS.name == "evals_data"
    assert PACKAGED_EVALS.parent.name == "sparkforge_aws"
