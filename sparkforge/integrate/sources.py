"""Onde moram `skills/` e `agents/` que a integracao grava (D3).

Duas origens, nesta ordem:

1. a raiz do repositorio, em desenvolvimento -- so vence com `pyproject.toml` e
   `skills/` presentes, para que um `site-packages/agents` de outro pacote nunca
   seja lido por engano;
2. `sparkforge/integrate/bundle/`, onde o `force-include` do wheel poe as duas
   pastas. Nao e `sparkforge/agents/`: esse nome ja e pacote Python.

Os parametros `repo_root` e `bundle` existem para o teste apontar as duas raizes
para `tmp_path`; o codigo de producao nunca os passa.
"""
from __future__ import annotations

from pathlib import Path

_AQUI = Path(__file__).resolve().parent
BUNDLE = _AQUI / "bundle"
REPO_ROOT = _AQUI.parents[1]


class SourcesError(RuntimeError):
    """`skills/` e `agents/` nao estao nem no repositorio nem no pacote."""


def _tem_conteudo(raiz: Path) -> bool:
    return (raiz / "skills").is_dir() and (raiz / "agents").is_dir()


def content_root(*, repo_root: Path | None = None, bundle: Path | None = None) -> Path:
    """A raiz que contem `skills/` e `agents/`."""
    repo = REPO_ROOT if repo_root is None else Path(repo_root)
    if (repo / "pyproject.toml").is_file() and _tem_conteudo(repo):
        return repo
    pacote = BUNDLE if bundle is None else Path(bundle)
    if _tem_conteudo(pacote):
        return pacote
    raise SourcesError(
        f"skills/ e agents/ nao encontrados em {repo} nem em {pacote}; "
        "reinstale o pacote: pip install --force-reinstall sparkforge-aws"
    )


def _raiz(root: Path | None) -> Path:
    return content_root() if root is None else Path(root)


def skills_dir(root: Path | None = None) -> Path:
    return _raiz(root) / "skills"


def agents_dir(root: Path | None = None) -> Path:
    return _raiz(root) / "agents"


def executors_dir(root: Path | None = None) -> Path:
    return agents_dir(root) / "executors"


def skill_names(root: Path | None = None) -> list[str]:
    return sorted(p.parent.name for p in skills_dir(root).glob("*/SKILL.md"))


def skill_files(root: Path | None = None) -> list[Path]:
    """Todo arquivo de toda skill, em qualquer profundidade."""
    base = skills_dir(root)
    return sorted(
        p for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.relative_to(base).parts
    )


def agent_files(root: Path | None = None) -> list[Path]:
    return sorted(p for p in agents_dir(root).glob("*.md") if p.is_file())


def executor_files(root: Path | None = None) -> list[Path]:
    return sorted(p for p in executors_dir(root).glob("*.md") if p.is_file())


__all__ = [
    "BUNDLE",
    "REPO_ROOT",
    "SourcesError",
    "agent_files",
    "agents_dir",
    "content_root",
    "executor_files",
    "executors_dir",
    "skill_files",
    "skill_names",
    "skills_dir",
]
