"""A regra de prova no que o host injeta, e os verbos que ela cita."""
import re
from pathlib import Path

import yaml

from sparkforge.adapters.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1]
MARCA_PT = "## Antes de responder sobre artefato, rode o verbo"
MARCA_EN = "## Before answering about an artifact, run the verb"


def _bloco(arquivo: str, marca: str) -> tuple[str, int, str]:
    texto = (ROOT / arquivo).read_text(encoding="utf-8")
    assert marca in texto, f"{arquivo} sem o bloco {marca!r}"
    inicio = texto.index(marca)
    fim = texto.find("\n## ", inicio + 1)
    return texto, inicio, texto[inicio : fim if fim != -1 else len(texto)]


def _tools(bloco: str) -> set[str]:
    return set(re.findall(r"`(sparkforge_[a-z_]+)`", bloco))


def test_claude_md_abre_com_a_regra_de_prova():
    texto, inicio, bloco = _bloco("CLAUDE.md", MARCA_PT)
    assert inicio < texto.index("Ao trabalhar em código PySpark")
    assert "fact_id" in bloco and "rule_id" in bloco
    assert _tools(bloco)


def test_agents_md_carrega_a_mesma_regra():
    _, _, pt = _bloco("CLAUDE.md", MARCA_PT)
    texto, inicio, en = _bloco("AGENTS.md", MARCA_EN)
    assert inicio < texto.index("This repository contains")
    assert "fact_id" in en and "rule_id" in en
    assert _tools(en) == _tools(pt)


def test_verbos_da_regra_existem_e_cobrem_a_suite():
    _, _, bloco = _bloco("CLAUDE.md", MARCA_PT)
    citadas = _tools(bloco)
    assert citadas <= set(TOOLS), sorted(citadas - set(TOOLS))
    suite = yaml.safe_load(
        (ROOT / "evals" / "agentic" / "fase0" / "suite.yaml").read_text(encoding="utf-8")
    )
    for pergunta in suite["questions"]:
        for item in pergunta["required_tools"]:
            alternativas = item if isinstance(item, list) else [item]
            assert any(f"sparkforge_{a}" in citadas for a in alternativas), (
                pergunta["id"],
                alternativas,
            )
