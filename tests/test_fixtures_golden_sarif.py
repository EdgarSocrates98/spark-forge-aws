"""Golden de `sparkforge report github` sobre o corpus `fixtures/sarif/`.

Cada caso traz `input/findings.json`, `input/facts.json` e `input/repo/` (a
arvore que existe no repositorio), mais `meta.yaml` com `source_roots`,
`fail_on` e `category`. O golden e o que a CLI grava e imprime:
`sparkforge.sarif`, `summary.md`, `annotations.txt` e `result.json` (contagens,
recusas, gate e exit code). `scripts/regen_fixtures.py::saidas_sarif` produz os
quatro pelo mesmo `_core.report_github` e o mesmo `report_github_textos` da CLI.

`_schema/` guarda o schema OASIS do SARIF 2.1.0 (ver `SOURCE.md`), e todo SARIF
dos goldens e validado contra ele. A comparacao normaliza CRLF para LF: o
checkout do Windows converte arquivo de texto, e foi o que quebrou o golden de
`host_transcript` no wheel do Windows (CI do PR #48).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "sarif"
ESQUEMA = FIXTURES / "_schema" / "sarif-schema-2.1.0.json"
ESQUEMA_SHA256 = "c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e"
SAIDAS = ("sparkforge.sarif", "summary.md", "annotations.txt", "result.json")


def _regen() -> Any:
    """`scripts/regen_fixtures.py` pelo caminho, sem por a raiz no `sys.path`.

    No gate de wheel a raiz no `sys.path` faria o `sparkforge` do repositorio
    vencer o instalado.
    """
    spec = importlib.util.spec_from_file_location(
        "regen_fixtures", ROOT / "scripts" / "regen_fixtures.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _casos() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir() and not p.name.startswith("_"))


def _texto(caminho: Path) -> str:
    return caminho.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _validador() -> jsonschema.Draft4Validator:
    return jsonschema.Draft4Validator(json.loads(_texto(ESQUEMA)))


def test_o_corpus_tem_os_quatro_casos():
    assert [p.name for p in _casos()] == ["misto", "pyspark_com_linha", "so_runtime", "terraform"]


def test_o_schema_e_o_da_oasis():
    """O schema versionado e o que o `SOURCE.md` registra, byte a byte (em LF)."""
    digest = hashlib.sha256(_texto(ESQUEMA).encode("utf-8")).hexdigest()
    assert digest == ESQUEMA_SHA256
    assert ESQUEMA_SHA256 in _texto(FIXTURES / "_schema" / "SOURCE.md")


@pytest.mark.parametrize("caso", _casos(), ids=lambda p: p.name)
class TestCaso:
    def test_saidas_batem_com_o_golden(self, caso):
        saidas = _regen().saidas_sarif(caso)
        for nome in SAIDAS:
            assert saidas[nome] == _texto(caso / "expected" / nome), nome

    def test_sarif_valida_contra_o_schema_oasis(self, caso):
        sarif = json.loads(_texto(caso / "expected" / "sparkforge.sarif"))
        assert not list(_validador().iter_errors(sarif))

    def test_nenhum_finding_some(self, caso):
        resultado = json.loads(_texto(caso / "expected" / "result.json"))
        findings = json.loads(_texto(caso / "input" / "findings.json"))
        contagem = resultado["counts"]
        assert contagem["located"] + contagem["refused"] == contagem["findings"] == len(findings)
        sarif = json.loads(_texto(caso / "expected" / "sparkforge.sarif"))
        assert len(sarif["runs"][0]["results"]) == contagem["located"]

    def test_a_cli_grava_imprime_e_sai_como_o_golden(self, caso, tmp_path, monkeypatch, capsys):
        """A CLI de verdade, numa copia do `repo/`: arquivos, stdout e exit code."""
        from sparkforge.adapters import _core, cli

        regen = _regen()
        monkeypatch.setattr(_core, "_versao_sparkforge", lambda: regen.SARIF_GOLDEN_VERSION)
        meta = yaml.safe_load(_texto(caso / "meta.yaml"))
        repo = tmp_path / "repo"
        shutil.copytree(caso / "input" / "repo", repo)
        argv = [
            "report", "github",
            "--findings", str(caso / "input" / "findings.json"),
            "--facts", str(caso / "input" / "facts.json"),
            "--repo", str(repo),
        ]
        for raiz in meta.get("source_roots") or []:
            argv += ["--source-root", raiz]
        if meta.get("fail_on"):
            argv += ["--fail-on", meta["fail_on"]]
        if meta.get("category"):
            argv += ["--category", meta["category"]]

        codigo = cli.main(argv)
        saida = capsys.readouterr()

        esperado = json.loads(_texto(caso / "expected" / "result.json"))
        assert codigo == esperado["exit_code"]
        assert saida.out.replace("\r\n", "\n") == _texto(caso / "expected" / "annotations.txt")
        gravado = repo / ".sparkforge" / "report"
        for nome in ("sparkforge.sarif", "summary.md"):
            assert _texto(gravado / nome) == _texto(caso / "expected" / nome), nome


def test_os_seis_motivos_de_recusa_aparecem_ou_estao_na_unidade():
    """`limite_do_github` e coberto em `tests/test_reporting_github.py` com
    limite reduzido: cinco mil resultados num golden seriam ruido."""
    from sparkforge.reporting.locate import MOTIVOS

    vistos = set()
    for caso in _casos():
        resultado = json.loads(_texto(caso / "expected" / "result.json"))
        vistos |= {r["reason"] for r in resultado["refused"]}
    assert vistos == set(MOTIVOS) - {"limite_do_github"}
