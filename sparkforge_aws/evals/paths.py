"""Localizacao das suites de `evals/agentic/` nos tres layouts.

As suites versionadas moram na raiz do repositorio por decisao de leitura (YAML
sem Python), e o wheel as copia para `sparkforge_aws/evals_data/agentic/` pelo
`force-include` -- o mesmo arranjo de `integrate/bundle`. `fixtures/` continua
fora do artefato (41 MiB de dado de desenvolvimento).

Precedencia, espelhando `knowledge_dir()`:

  1. `SPARKFORGE_AWS_EVALS` -- override explicito; tem de conter
     `agentic/<suite>`, senao `EvalsError` (override quebrado e configuracao,
     nao ausencia de recurso). Divergencia deliberada do modelo §4.3 (env
     abaixo do workspace): aqui env e escolha explicita do operador e por
     isso vence o cwd — consistente com `knowledge_dir()`/`catalog_dir()`;
  2. `<cwd>/evals` -- o workspace do usuario continua podendo ter suites
     proprias, e elas vencem as versionadas;
  3. a raiz do repositorio (com marcador `pyproject.toml`, como em
     `integrate/sources.py`, para nunca ler um `site-packages/evals`
     estranho);
  4. `sparkforge_aws/evals_data/` -- o que o wheel carrega.

A resolucao e por SUITE, nao por raiz: um workspace com `evals/agentic/` que
so tem suites locais ainda enxerga as versionadas no pacote.
"""
from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PACKAGE_ROOT.parent
PACKAGED_EVALS = _PACKAGE_ROOT / "evals_data"


class EvalsError(ValueError):
    """Override de evals quebrado, ou suite inexistente em todas as raizes."""


def _bases(cwd: Path) -> list[Path]:
    override = os.environ.get("SPARKFORGE_AWS_EVALS") or os.environ.get("SPARK_FORGE_AWS_EVALS")
    if override:
        return [Path(override).expanduser() / "agentic"]
    bases = [cwd / "evals" / "agentic"]
    if (_REPO_ROOT / "pyproject.toml").is_file():
        bases.append(_REPO_ROOT / "evals" / "agentic")
    bases.append(PACKAGED_EVALS / "agentic")
    return bases


def suite_dir(nome: str, *, cwd: Path | None = None) -> Path:
    """O diretorio `evals/agentic/<nome>` resolvido, ou `EvalsError`.

    `nome` e um nome de diretorio, nao um path: separadores, `..` e paths
    absolutos sao recusados — sem isto um caller (CLI ou MCP) poderia
    atravessar para fora das raizes de eval.
    """
    if not nome or Path(nome).name != nome or nome in (".", ".."):
        raise EvalsError(f"nome de suite invalido: {nome!r}")
    override = os.environ.get("SPARKFORGE_AWS_EVALS") or os.environ.get("SPARK_FORGE_AWS_EVALS")
    candidatos = [b / nome for b in _bases((cwd or Path.cwd()).resolve())]
    for candidato in candidatos:
        if candidato.is_dir():
            return candidato
    if override:
        env_name = (
            "SPARKFORGE_AWS_EVALS"
            if os.environ.get("SPARKFORGE_AWS_EVALS")
            else "SPARK_FORGE_AWS_EVALS"
        )
        raise EvalsError(
            f"{env_name} aponta para {Path(override).expanduser()}, "
            f"que nao contem agentic/{nome}"
        )
    raise EvalsError(
        f"suite {nome!r} nao encontrada em nenhuma raiz de evals: "
        + ", ".join(str(c) for c in candidatos)
    )


def suites_disponiveis(*, cwd: Path | None = None) -> list[str]:
    """Os nomes de suite visiveis (workspace + versionadas), ordenados.

    Override env quebrado e configuracao, nao "lista vazia": se a var
    aponta para algo inexistente o erro nomeia a var, igual a
    `suite_dir` — `evals list` nunca encobre um override invalido.
    """
    override = os.environ.get("SPARKFORGE_AWS_EVALS") or os.environ.get("SPARK_FORGE_AWS_EVALS")
    bases = _bases((cwd or Path.cwd()).resolve())
    if override and not bases[0].is_dir():
        env_name = (
            "SPARKFORGE_AWS_EVALS"
            if os.environ.get("SPARKFORGE_AWS_EVALS")
            else "SPARK_FORGE_AWS_EVALS"
        )
        raise EvalsError(
            f"{env_name} aponta para {Path(override).expanduser()}, "
            "que nao contem agentic/"
        )
    nomes: set[str] = set()
    for base in bases:
        if base.is_dir():
            nomes.update(p.name for p in base.iterdir() if p.is_dir())
    return sorted(nomes)


__all__ = ["EvalsError", "PACKAGED_EVALS", "suite_dir", "suites_disponiveis"]
