"""L2 do §15 pela porta de `_core`: arvore principal intacta, id estavel, limpeza e erros."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sparkforge.adapters import _core
from sparkforge.change.refusals import ARQUIVO_FORA_DA_COPIA, DIFF_NAO_APLICA

JOB = 'def configurar(spark):\n    spark.conf.set("spark.sql.shuffle.partitions", "800")\n'
PATCH = (
    "--- a/lib/job.py\n+++ b/lib/job.py\n@@ -1,2 +1,2 @@\n def configurar(spark):\n"
    '-    spark.conf.set("spark.sql.shuffle.partitions", "800")\n+    return spark\n'
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "lib").mkdir(parents=True)
    (repo / "lib" / "job.py").write_text(JOB, encoding="utf-8", newline="\n")
    return repo


def _hashes(raiz: Path) -> dict[str, str]:
    return {
        p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raiz.rglob("*"))
        if p.is_file() and not p.relative_to(raiz).as_posix().startswith(".sparkforge/sandbox/")
    }


def _patch(tmp_path: Path, texto: str = PATCH) -> str:
    alvo = tmp_path / "host.patch"
    alvo.write_text(texto, encoding="utf-8", newline="\n")
    return str(alvo)


def test_arvore_intacta_id_estavel_e_relatorio(tmp_path):
    repo = _repo(tmp_path)
    antes = _hashes(repo)
    primeiro = _core.change_sandbox(str(repo), diff_path=_patch(tmp_path))
    segundo = _core.change_sandbox(str(repo), diff_path=_patch(tmp_path))
    assert primeiro == segundo and primeiro["applied"] is True
    assert _hashes(repo) == antes
    base = repo / primeiro["sandbox"]
    assert json.loads((base / "report.json").read_text(encoding="utf-8")) == primeiro
    assert (base / "before" / "lib" / "job.py").read_text(encoding="utf-8") == JOB
    assert "return spark" in (base / "after" / "lib" / "job.py").read_text(encoding="utf-8")


def test_recusa_nao_cria_nada_no_disco(tmp_path):
    repo = _repo(tmp_path)
    errado = _patch(tmp_path, PATCH.replace('"800"', '"900"'))
    resultado = _core.change_sandbox(str(repo), diff_path=errado)
    assert [r["reason"] for r in resultado["refused"]] == [DIFF_NAO_APLICA]
    assert not (repo / ".sparkforge").exists()


def test_diretorio_podado_vira_arquivo_fora_da_copia(tmp_path):
    repo = _repo(tmp_path)
    (repo / "vendor").mkdir()
    (repo / "vendor" / "x.py").write_text("a = 1\n", encoding="utf-8", newline="\n")
    texto = "--- a/vendor/x.py\n+++ b/vendor/x.py\n@@ -1 +1 @@\n-a = 1\n+a = 2\n"
    resultado = _core.change_sandbox(str(repo), diff_path=_patch(tmp_path, texto))
    (recusa,) = resultado["refused"]
    assert recusa["reason"] == ARQUIVO_FORA_DA_COPIA and "DIRECTORY_IGNORED" in recusa["detail"]


def test_artefatos_coletados_entram_na_copia(tmp_path):
    repo = _repo(tmp_path)
    artefatos = repo / ".sparkforge" / "artifacts"
    artefatos.mkdir(parents=True)
    (artefatos / "manifest.json").write_text("[]\n", encoding="utf-8")
    resultado = _core.change_sandbox(str(repo), diff_path=_patch(tmp_path))
    copia = repo / resultado["before"] / ".sparkforge" / "artifacts" / "manifest.json"
    assert copia.read_text(encoding="utf-8") == "[]\n"


def test_limpeza_confinada(tmp_path):
    repo = _repo(tmp_path)
    feito = _core.change_sandbox(str(repo), diff_path=_patch(tmp_path))
    limpo = _core.change_sandbox(str(repo), clean=True)
    assert limpo["removed"] == [feito["id"]] and limpo["main_tree_touched"] is False
    assert not (repo / ".sparkforge" / "sandbox").exists()
    assert (repo / "lib" / "job.py").read_text(encoding="utf-8") == JOB


@pytest.mark.parametrize(
    "chamada",
    [
        lambda t: _core.change_sandbox(str(t / "nao-existe"), diff_path="x.patch"),
        lambda t: _core.change_sandbox(str(_repo(t)), diff_path=str(t / "nada.patch")),
        lambda t: _core.change_sandbox(str(_repo(t))),
        lambda t: _core.change_plan([], str(t)),
        lambda t: _core.change_plan(["f.json"], str(t), from_tune=True, sets=["a=1"]),
        lambda t: _core.change_plan(["f.json"], str(t)),
        lambda t: _core.change_plan(["f.json"], str(t / "nao-existe"), sets=["a=1"]),
    ],
)
def test_erro_de_entrada_diz_o_comando(chamada, tmp_path):
    with pytest.raises(_core.AdapterError) as exc:
        chamada(tmp_path)
    assert "sparkforge" in str(exc.value) and exc.value.exit_code == 2


def test_set_malformado(tmp_path):
    fatos = tmp_path / "f.json"
    fatos.write_text("[]", encoding="utf-8")
    with pytest.raises(_core.AdapterError, match="chave=valor"):
        _core.change_plan([str(fatos)], str(tmp_path), sets=["sem-igual"])
