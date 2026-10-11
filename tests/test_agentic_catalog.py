"""`docs/agentic-catalog.md` e o que os canonicos geram hoje.

Coordenador, executor ou skill novo/alterado sem regerar o catalogo derruba
este teste. Conserto: `python scripts/gen_agentic_catalog.py`.

O catalogo e a ficha §11 do prompt de produto: um documento que so lista
nomes seria exatamente o que o §11 proibe -- por isso o teste tambem exige
que cada ficha carregue os campos obrigatorios.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location(
        "gen_agentic_catalog", ROOT / "scripts" / "gen_agentic_catalog.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def paginas(gerador):
    return gerador.render_all()


def test_catalogo_em_dia(gerador, paginas):
    diferentes, sobrando = gerador.divergencias(paginas)
    assert not diferentes, (
        f"catalogo velho em {diferentes}. "
        "Rode `python scripts/gen_agentic_catalog.py`."
    )
    assert not sobrando


def test_toda_entidade_tem_ficha(paginas):
    texto = next(iter(paginas.values()))
    fichas = [t for t in texto.split("### `")[1:] if t.strip()]
    assert len(fichas) == 14 + 5 + 60


def test_campos_do_contrato_secao_11(paginas):
    import re

    texto = next(iter(paginas.values()))
    secoes = texto.split("\n## ")
    por_titulo = {
        s.splitlines()[0]: s for s in secoes if s.splitlines()
    }
    campos_agente = {
        "NAME", "PURPOSE", "DOMAIN", "WHEN_TO_USE", "WHEN_NOT_TO_USE",
        "TRIGGERS", "SUPPORTED_HOSTS", "REQUIRED_SKILLS", "AVAILABLE_TOOLS",
        "MCP_DEPENDENCIES", "INPUTS", "EXPECTED_OUTPUT", "VERIFICATION",
        "EXAMPLE_PROMPT", "LIMITATIONS",
    }
    campos_skill = {
        "NAME", "PURPOSE", "TRIGGERS", "SUPPORTED_HOSTS",
        "ACTIVATION_METHOD", "RELATED_AGENTS", "RELATED_MCP_TOOLS",
        "EXAMPLE", "VERIFICATION",
    }
    for titulo, esperado in (
        ("Coordenadores", campos_agente),
        ("Executores", campos_agente),
        ("Skills", campos_skill),
    ):
        for ficha in por_titulo[titulo].split("### `")[1:]:
            campos = set(re.findall(r"^\| ([A-Z_]+) \|", ficha, re.M))
            faltando = esperado - campos
            assert not faltando, f"{ficha[:40]}: {faltando}"
