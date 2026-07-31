#!/usr/bin/env python3
"""Gera `requirements.txt` a partir de `pyproject.toml`, e confere o espelho.

Por que este arquivo existe
===========================

`pyproject.toml` continua sendo a UNICA fonte da verdade das dependencias.
`requirements.txt` e espelho gerado, pelo mesmo motivo que `.claude/`,
`.agents/` e `.github/` sao espelhos gerados de `skills/`: uma ferramenta de
fora do projeto precisa de um formato que ela leia.

No caso, ferramenta de SCA. O `pyproject.toml` deste repo usa backend setuptools
e nao tem lockfile, e o suporte a pip do Snyk espera `requirements.txt`,
`poetry.lock` ou `uv.lock` -- sem um dos tres, o scan de dependencia
simplesmente nao roda, nem local nem em CI. Um scan que nao roda nao e um scan
que passa; e um scan ausente, e a diferenca importa exatamente do mesmo jeito
que `pyspark.unresolved` importa no analisador.

A alternativa era `uv lock`, que da pinning por hash e e melhor a longo prazo.
Ficou de fora aqui porque adiciona uv ao caminho de build de todo mundo, e
porque o objetivo imediato e tornar o scan possivel, nao trocar a gestao de
dependencia do projeto. Migrar depois nao e bloqueado por esta decisao: quando
houver lock, este espelho some junto com o script.

O risco obvio de espelho e drift -- duas declaracoes divergindo em silencio.
Por isso `--check`, que roda no CI ao lado de `sync_skills.py --check`. Uma
dependencia adicionada ao `pyproject.toml` e esquecida aqui quebra a build,
igual a uma skill editada no espelho errado.

Uso
===

    python scripts/gen_requirements.py            # reescreve requirements.txt
    python scripts/gen_requirements.py --check    # falha se estiver defasado
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
REQUIREMENTS = ROOT / "requirements.txt"

HEADER = """\
# GERADO por scripts/gen_requirements.py -- NAO EDITE A MAO.
#
# Fonte da verdade: pyproject.toml. Este espelho existe porque ferramenta de SCA
# nao le pyproject.toml com backend setuptools sem lockfile, e scan que nao roda
# nao e scan que passa.
#
# Inclui as dependencias do nucleo E de todos os extras, de proposito: o extra
# `mcp` e o que traz a arvore transitiva maior, e deixar ele de fora esconderia
# justamente a parte que mais precisa ser vigiada.
#
# Regenere com: python scripts/gen_requirements.py
"""

# Captura o conteudo de `dependencies = [...]` e de cada extra em
# `[project.optional-dependencies]`, parando em `[project.scripts]`.
_ARRAY = re.compile(
    r"^\s*(?:dependencies|[A-Za-z][\w-]*)\s*=\s*\[(.*?)\]", re.DOTALL | re.MULTILINE
)
_REQ = re.compile(r'"([^"]+)"')


def _section(text: str) -> str:
    """Do inicio de [project] ate antes de [project.scripts].

    Recortar antes de `[project.scripts]` evita capturar o entry point
    `sparkforge = "sparkforge.adapters.cli:main"`, que nao e requisito.
    """
    start = text.find("[project]")
    end = text.find("[project.scripts]")
    if start == -1:
        raise SystemExit("pyproject.toml sem secao [project]")
    return text[start:end] if end != -1 else text[start:]


def requirements_from_pyproject() -> list[str]:
    """Todos os requisitos declarados, deduplicados, em ordem de aparicao."""
    section = _section(PYPROJECT.read_text(encoding="utf-8"))

    found: list[str] = []
    seen: set[str] = set()
    for array in _ARRAY.findall(section):
        for requirement in _REQ.findall(array):
            # Um requisito sempre comeca com o nome do pacote. Descarta valores
            # que casaram por acidente (build-backend, nome do projeto).
            if not re.match(r"^[A-Za-z][A-Za-z0-9_.\-]*\s*(?:[<>=!~\[]|$)", requirement):
                continue
            key = requirement.lower().replace(" ", "")
            if key not in seen:
                seen.add(key)
                found.append(requirement)
    return found


def render() -> str:
    return HEADER + "\n".join(requirements_from_pyproject()) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="Falha se estiver defasado.")
    args = parser.parse_args(argv)

    expected = render()

    if args.check:
        if not REQUIREMENTS.is_file():
            print("requirements.txt ausente; rode scripts/gen_requirements.py", file=sys.stderr)
            return 1
        current = REQUIREMENTS.read_text(encoding="utf-8")
        if current != expected:
            print(
                "requirements.txt defasado em relacao a pyproject.toml.\n"
                "Rode: python scripts/gen_requirements.py",
                file=sys.stderr,
            )
            return 1
        print("OK: requirements.txt reflete pyproject.toml.")
        return 0

    REQUIREMENTS.write_text(expected, encoding="utf-8", newline="\n")
    print(f"{REQUIREMENTS.relative_to(ROOT)}: {len(requirements_from_pyproject())} requisitos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
