"""As skills `sdd-*` e os templates de `docs/sdd/templates/` (feature SDD_SKILLS).

Os templates sao artefatos validos de uma feature de exemplo: o teste os copia
para um repositorio em `tmp_path`, carimba em ordem e exige o `check` limpo. Assim
o formato que as skills ensinam e o formato que o gate aceita nao divergem.
"""

from __future__ import annotations

from pathlib import Path

from sparkforge.sdd import PHASES
from sparkforge.sdd.checks import check
from sparkforge.sdd.stamp import stamp

ROOT = Path(__file__).resolve().parents[1]
SKILLS_SDD = ("sdd-explore", "sdd-define", "sdd-design", "sdd-plan", "sdd-build", "sdd-ship")


def _texto_da_skill(nome: str) -> str:
    return (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")


def test_seis_skills_existem():
    for nome in SKILLS_SDD:
        texto = _texto_da_skill(nome)
        assert texto.startswith("---\nname: " + nome + "\n"), nome
        for secao in ("## Quando NÃO usar", "## Referência rápida", "## Red flags"):
            assert secao in texto, (nome, secao)
        assert "sparkforge sdd check" in texto, nome


def test_templates_formam_feature_valida(tmp_path):
    """Copia os seis templates para uma feature, carimba em ordem e confere."""
    origem = ROOT / "docs" / "sdd" / "templates"
    destino = tmp_path / "docs" / "sdd" / "EXEMPLO"
    destino.mkdir(parents=True)
    for fase in PHASES:
        (destino / f"{fase}.md").write_bytes((origem / f"{fase}.md").read_bytes())
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_exemplo.py").write_bytes(b"def test_exemplo():\n    pass\n")
    for fase in PHASES[1:]:
        stamp(tmp_path, f"docs/sdd/EXEMPLO/{fase}.md")
    relatorio = check(tmp_path)
    assert relatorio["features"] == ["EXEMPLO"], relatorio
    assert relatorio["refused"] == [], relatorio
    assert relatorio["unresolved"] == [], relatorio
    assert relatorio["ok"] is True


def test_templates_nao_viram_feature_no_repositorio():
    """`docs/sdd/templates/` fica fora da descoberta: o nome nao casa o padrao."""
    relatorio = check(ROOT)
    assert "templates" not in relatorio["features"]
    assert "EXEMPLO" not in relatorio["features"]
