"""Nucleo do SDD proprio: contrato conferivel e gates com nome.

Nenhuma fixture estatica: hash de upstream gravado em arquivo versionado e o caso
que o checkout do Windows com `core.autocrlf=true` ja quebrou (PR #63). Toda
feature e montada em `tmp_path`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.checks import change_kinds, schema_for
from sparkforge.sdd.load import discover, load_artifact, split_frontmatter

ROOT = Path(__file__).resolve().parents[1]


def test_fases_e_raiz_padrao():
    assert PHASES == ("explore", "define", "design", "plan", "build_report", "ship")
    assert DEFAULT_ROOT == "docs/sdd"


def test_split_frontmatter_separa_bloco_e_corpo():
    bloco, corpo = split_frontmatter("---\na: 1\n---\ncorpo\n")
    assert bloco == "a: 1\n"
    assert corpo == "corpo\n"


def test_split_frontmatter_sem_cerca_devolve_none():
    assert split_frontmatter("a: 1\n") == (None, "a: 1\n")
    assert split_frontmatter("---\na: 1\n")[0] is None


def test_load_artifact_yaml_quebrado_diz_a_linha(tmp_path):
    arquivo = tmp_path / "define.md"
    arquivo.write_bytes(b"---\nsdd: 1\nfeature: [\n---\n")
    artefato = load_artifact(arquivo)
    assert artefato.meta is None
    assert "YAML invalido" in artefato.error
    assert "linha" in artefato.error


def test_load_artifact_nao_mapeamento(tmp_path):
    arquivo = tmp_path / "define.md"
    arquivo.write_bytes(b"---\n- a\n---\n")
    assert load_artifact(arquivo).error == "frontmatter precisa ser um mapeamento YAML"


def test_discover_so_pega_fase_na_profundidade_certa(tmp_path):
    raiz = tmp_path / "docs" / "sdd"
    (raiz / "F1").mkdir(parents=True)
    (raiz / "F1" / "define.md").write_bytes(b"---\n---\n")
    (raiz / "F1" / "notas.md").write_bytes(b"x")
    (raiz / "templates").mkdir()
    (raiz / "archive" / "F0").mkdir(parents=True)
    (raiz / "archive" / "F0" / "define.md").write_bytes(b"x")
    assert discover(raiz) == {"F1": {"define": raiz / "F1" / "define.md"}}


@pytest.mark.parametrize("fase", PHASES)
def test_todo_schema_carrega_e_fecha_propriedades(fase):
    schema = schema_for(fase)
    assert schema["additionalProperties"] is False
    for campo in ("sdd", "feature", "phase", "profile", "status"):
        assert campo in schema["required"]


def test_change_kinds_casa_com_os_titulos_do_documento():
    """Deriva nos dois sentidos: titulo sem chave, ou chave sem titulo."""
    texto = (ROOT / "docs" / "gates-por-mudanca.md").read_text(encoding="utf-8")
    linhas = texto.splitlines()
    titulos: set[str] = set()
    for i, linha in enumerate(linhas):
        if not linha.startswith("## "):
            continue
        titulo = linha[3:].strip()
        # o titulo da secao de lastro continua na linha seguinte
        if i + 1 < len(linhas) and linhas[i + 1].startswith("## `"):
            titulo = f"{titulo} {linhas[i + 1][3:].strip()}"
        titulos.add(titulo)
    titulos = {t for t in titulos if not t.startswith("`docs/")}
    titulos.discard("Quando nada acima serve")
    secoes = {v["section"] for v in change_kinds().values()}
    assert secoes == titulos
    for chave, valor in change_kinds().items():
        assert re.fullmatch(r"[a-z][a-z0-9_]*", chave)
        assert valor["registries"], chave
