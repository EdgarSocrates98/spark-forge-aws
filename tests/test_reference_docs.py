"""A referencia de `docs/guia/referencia/` e a que o codigo gera hoje.

Tool, verbo, agent ou skill novo sem regerar a referencia derruba este teste.
Conserto: `python scripts/gen_reference_docs.py`.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location(
        "gen_reference_docs", ROOT / "scripts" / "gen_reference_docs.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def paginas(gerador):
    return gerador.render_all()


def test_referencia_em_dia(gerador, paginas):
    diferentes, sobrando = gerador.divergencias(paginas)
    assert not diferentes, (
        f"referencia velha em {len(diferentes)} paginas (ex.: {diferentes[:5]}). "
        "Rode `python scripts/gen_reference_docs.py`."
    )
    assert not sobrando, f"paginas sem origem no codigo: {sobrando}"


def test_toda_tool_e_skill_tem_pagina(gerador, paginas):
    from sparkforge.adapters.tools import TOOLS

    relativas = {p.relative_to(gerador.DEST).as_posix() for p in paginas}
    faltando = [f"tools/{t}.md" for t in TOOLS if f"tools/{t}.md" not in relativas]
    faltando += [
        f"skills/{s}.md" for s in gerador._nomes_de_skill() if f"skills/{s}.md" not in relativas
    ]
    assert not faltando, faltando


GUIA = ROOT / "docs" / "guia"


def _guias() -> list[Path]:
    """Os manuais escritos a mao: tudo em `docs/guia/` fora da referencia."""
    return sorted(
        p for p in GUIA.rglob("*.md") if "referencia" not in p.relative_to(GUIA).parts
    )


def test_todo_comando_que_os_guias_ensinam_existe():
    """Mesma disciplina de `test_docs_coverage`: verbo citado em bloco de codigo
    ou entre crases tem que existir no parser real."""
    import argparse

    from sparkforge.adapters.cli import build_parser

    verbos: set[str] = set()
    for acao in build_parser()._actions:
        if isinstance(acao, argparse._SubParsersAction):
            verbos |= set(acao.choices)
    inventados = []
    for guia in _guias():
        texto = guia.read_text(encoding="utf-8")
        # Verbo e palavra que comeca com letra: `--help`, `<comando>` e a linha
        # de saida `sparkforge 0.5.0` nao citam verbo.
        citados = set(re.findall(r"(?m)^\s*sparkforge\s+([a-z][a-z0-9-]*)", texto))
        citados |= set(re.findall(r"`sparkforge\s+([a-z][a-z0-9-]*)", texto))
        inventados += [f"{guia.relative_to(ROOT).as_posix()}: {v}" for v in citados - verbos]
    assert not inventados, inventados


def test_links_relativos_dos_guias_resolvem():
    quebrados = []
    for guia in _guias():
        for alvo in re.findall(r"\]\(([^)\s#]+)(?:#[^)]*)?\)", guia.read_text(encoding="utf-8")):
            if alvo.startswith(("http://", "https://", "mailto:")):
                continue
            if not (guia.parent / alvo).resolve().exists():
                quebrados.append(f"{guia.relative_to(ROOT).as_posix()} -> {alvo}")
    assert not quebrados, quebrados[:30]


def test_links_relativos_da_referencia_resolvem(paginas):
    geradas = {p.resolve() for p in paginas}
    quebrados = []
    for caminho, texto in paginas.items():
        for alvo in re.findall(r"\]\(([^)\s#]+)(?:#[^)]*)?\)", texto):
            if alvo.startswith(("http://", "https://", "mailto:")):
                continue
            destino = (caminho.parent / alvo).resolve()
            if destino not in geradas and not destino.exists():
                quebrados.append(f"{caminho.relative_to(ROOT).as_posix()} -> {alvo}")
    assert not quebrados, quebrados[:20]
