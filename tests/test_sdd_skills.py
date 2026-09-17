"""As skills `sdd-*` e os templates de `docs/sdd/templates/` (feature SDD_SKILLS).

Os templates sao artefatos validos de uma feature de exemplo: o teste os copia
para um repositorio em `tmp_path`, carimba em ordem e exige o `check` limpo. Assim
o formato que as skills ensinam e o formato que o gate aceita nao divergem.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from sparkforge.adapters.cli import build_parser
from sparkforge.sdd import PHASES
from sparkforge.sdd.checks import check
from sparkforge.sdd.stamp import stamp

ROOT = Path(__file__).resolve().parents[1]
SKILLS_SDD = ("sdd-explore", "sdd-define", "sdd-design", "sdd-plan", "sdd-build", "sdd-ship")


# `sparkforge <verbo>` entre crases, com o subcomando quando houver palavra minuscula
# logo depois; flag (`--x`) e marcador (`<F>`) encerram a captura.
_VERBO_CITADO = re.compile(r"`sparkforge ([a-z][a-z-]*(?: [a-z][a-z-]*)?)")


def _texto_da_skill(nome: str) -> str:
    return (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")


def _verbos_citados(texto: str) -> list[str]:
    return sorted(set(_VERBO_CITADO.findall(texto)))


def _aceito_pelo_parser(parser: argparse.ArgumentParser, verbo: str) -> bool:
    """`--help` sai com 0 quando o parser conhece o caminho; verbo inventado sai com 2."""
    try:
        parser.parse_args([*verbo.split(), "--help"])
    except SystemExit as saida:
        return saida.code == 0
    return False


# o comando inteiro entre crases; `<...>` vira valor ficticio antes de separar
_COMANDO_CITADO = re.compile(r"`sparkforge ([^`]*)`")
_MARCADOR = re.compile(r"<[^<>]*>")


def _subcomandos(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for acao in parser._actions:
        if isinstance(acao, argparse._SubParsersAction):
            return acao.choices
    return {}


def _flags_recusadas(parser: argparse.ArgumentParser, comando: str) -> list[str]:
    """As `--flags` do comando citado que o subparser do proprio verbo nao conhece."""
    tokens = _MARCADOR.sub("X", comando).split()
    atual = parser
    while tokens and tokens[0] in _subcomandos(atual):
        atual = _subcomandos(atual)[tokens.pop(0)]
    conhecidas = {opcao for acao in atual._actions for opcao in acao.option_strings}
    return [token for token in tokens if token.startswith("--") and token not in conhecidas]


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


def test_comandos_citados_existem(capsys):
    """Todo `sparkforge <verbo> [<sub>]` entre crases nas skills sdd-* e aceito pelo parser,
    e toda `--flag` citada existe no subparser daquele verbo."""
    parser = build_parser()
    for nome in SKILLS_SDD:
        texto = _texto_da_skill(nome)
        verbos = _verbos_citados(texto)
        assert "sdd check" in verbos, nome
        recusados = [verbo for verbo in verbos if not _aceito_pelo_parser(parser, verbo)]
        assert not recusados, (nome, recusados)
        flags = [
            (comando, flag)
            for comando in _COMANDO_CITADO.findall(texto)
            for flag in _flags_recusadas(parser, comando)
        ]
        assert not flags, (nome, flags)


def test_o_detector_recusa_verbo_inventado(capsys):
    """Guarda do teste acima: sem isto, um detector quebrado passaria por vacuidade."""
    parser = build_parser()
    assert _verbos_citados("rode `sparkforge sdd verify --repo .` e `sparkforge judge`") == [
        "judge",
        "sdd verify",
    ]
    assert not _aceito_pelo_parser(parser, "sdd verify")
    assert _aceito_pelo_parser(parser, "sdd check")
    assert _aceito_pelo_parser(parser, "judge")


def test_o_detector_recusa_flag_inventada():
    """Guarda da conferencia de flags: sem isto, o AC3 de SDD_SKILLS passaria por vacuidade."""
    parser = build_parser()
    assert _flags_recusadas(parser, "funcval compare --plan <p> --out <ref do AC>") == []
    assert _flags_recusadas(parser, "change propose --sandbox <id> --funcaval x") == ["--funcaval"]
    assert _flags_recusadas(parser, "sdd check --repo . --raiz docs") == ["--raiz"]
    # flag de outro verbo nao vale aqui
    assert _flags_recusadas(parser, "benchmark --before a --funcval b") == ["--funcval"]


def _descricao(nome: str) -> str:
    return re.search(r"^description: (.*)$", _texto_da_skill(nome), re.M).group(1)


def test_descricoes_so_com_gatilho():
    for nome in SKILLS_SDD:
        descricao = _descricao(nome)
        assert descricao.startswith("Use quando"), nome
        assert len(descricao) <= 320, (nome, len(descricao))
        for resumo in ("Grava ", "fecha com", "fechando com"):
            assert resumo not in descricao, (nome, resumo)


def test_credito_das_bases():
    """AgentSpec e superpowers creditados, com licenca e o que veio de cada um."""
    texto = (ROOT / "vendor" / "CREDITS.md").read_text(encoding="utf-8")
    for trecho in ("luanmorenommaciel/agentspec", "obra/superpowers", "MIT", "sdd-"):
        assert trecho in texto, trecho
    for nome in SKILLS_SDD:
        assert f"`{nome}`" in texto, nome
