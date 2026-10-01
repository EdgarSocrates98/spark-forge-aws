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

# Localiza o INICIO de `dependencies = [...]` e de cada extra em
# `[project.optional-dependencies]`, parando em `[project.scripts]`. So o
# inicio: onde o array termina e trabalho do scanner abaixo, nao da regex.
#
# Por que nao regex ate o fim: um array TOML pode ter comentario de linha no
# meio (`# pip install -e ".[dev]"`), e esse comentario pode conter `]` ou
# `[` sem fechar nem abrir nada de verdade. Regex nao-guloso (`.*?\]`) para
# no PRIMEIRO `]` do texto, esteja ele dentro de comentario ou nao -- e um
# `]` de comentario truncando a captura descarta em silencio todo requisito
# que vem depois dele, exatamente o defeito que mordeu `build>=1.0` nesta
# sessao. Regex ganancioso (`.*\]`) erra para o outro lado: vai ate o
# ULTIMO `]` do arquivo, atravessando arrays seguintes. Nenhum dos dois
# entende profundidade de colchete, e comentario/string dentro do TOML nao
# tem como ser modelado por uma classe de caracteres sem, no fim, reescrever
# um mini-parser dentro da regex -- nesse ponto e mais claro escrever o
# parser como codigo. `_scan_array`, abaixo, conta colchete de verdade e
# pula comentario e string inteiros antes de olhar para `[` ou `]`.
_ARRAY_START = re.compile(r"^\s*(?:dependencies|[A-Za-z][\w-]*)\s*=\s*\[", re.MULTILINE)


def _scan_array(text: str, open_bracket: int) -> tuple[list[str], int]:
    """Varre `text` a partir do `[` em `open_bracket` e devolve as strings
    entre aspas achadas dentro do array, mais o indice logo apos o `]` que
    fecha esse array (contando profundidade, entao aninhamento funciona).

    Comentario (`#` ate o fim da linha) e pulado inteiro antes de qualquer
    checagem de colchete ou aspas -- por isso `]`/`[`/`#` dentro de
    comentario nao contam. String entre aspas tambem e pulada inteira antes
    de procurar `#` -- por isso `#` dentro de string nao vira comentario.
    """
    n = len(text)
    depth = 0
    i = open_bracket
    strings: list[str] = []
    while i < n:
        ch = text[i]
        if ch == "#":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl + 1
            continue
        if ch == '"' or ch == "'":
            quote = ch
            j = i + 1
            while j < n and text[j] != quote:
                if quote == '"' and text[j] == "\\":
                    j += 1
                j += 1
            if depth >= 1:
                strings.append(text[i + 1 : j])
            i = j + 1
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return strings, i + 1
        i += 1
    raise SystemExit("array sem colchete de fechamento em pyproject.toml")


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
    for match in _ARRAY_START.finditer(section):
        strings, _ = _scan_array(section, match.end() - 1)
        for requirement in strings:
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
