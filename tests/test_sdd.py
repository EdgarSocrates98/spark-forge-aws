"""Nucleo do SDD proprio: contrato conferivel e gates com nome.

Nenhuma fixture estatica: hash de upstream gravado em arquivo versionado e o caso
que o checkout do Windows com `core.autocrlf=true` ja quebrou (PR #63). Toda
feature e montada em `tmp_path`.
"""

from __future__ import annotations

from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.load import discover, load_artifact, split_frontmatter


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
