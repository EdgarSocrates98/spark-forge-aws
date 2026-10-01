"""Golden do `sparkforge scan` (§22), de ponta a ponta pela CLI.

Cada caso de `fixtures/scan/` tem um `repo/` sintetico (codigo e, quando cabe,
`.sparkforge/artifacts/` com manifesto e sha256 reais). O scan roda sobre uma
COPIA em `tmp_path`, porque ele grava em `<repo>/.sparkforge/scan/`.

Regenerar depois de mudanca DELIBERADA:
`SPARKFORGE_REGEN_SCAN=1 pytest tests/test_fixtures_golden_scan.py`.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters import _core
from sparkforge.adapters.cli import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "scan"
REGEN = os.environ.get("SPARKFORGE_REGEN_SCAN") == "1"
CASOS = sorted(p.name for p in FIXTURES.iterdir() if (p / "meta.yaml").is_file())


def _copia(caso: str, tmp_path: Path) -> Path:
    destino = tmp_path / "repo"
    shutil.copytree(FIXTURES / caso / "repo", destino)
    return destino


def _rodar(repo: Path, capsys, *extra: str, esperado: int = 0) -> dict:
    assert main(["scan", str(repo), *extra]) == esperado
    return json.loads(capsys.readouterr().out)


def _estavel(resumo: dict) -> dict:
    """Tira do resumo o que depende do caminho da copia."""
    resumo = json.loads(json.dumps(resumo))
    if resumo.get("runtime"):
        resumo["runtime"].pop("detected_from", None)
    return resumo


@pytest.mark.parametrize("caso", CASOS)
def test_golden(caso, tmp_path, capsys):
    meta = yaml.safe_load((FIXTURES / caso / "meta.yaml").read_text(encoding="utf-8"))
    resumo = _estavel(_rodar(_copia(caso, tmp_path), capsys, *(meta.get("args") or [])))
    esperado = FIXTURES / caso / "expected" / "summary.json"
    texto = json.dumps(resumo, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if REGEN:
        esperado.parent.mkdir(parents=True, exist_ok=True)
        esperado.write_text(texto, encoding="utf-8", newline="\n")
    assert texto == esperado.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_scan_igual_ao_fluxo_a_mao(tmp_path, capsys):
    """SC1: analyze por arquivo -> fuse -> judge, feito a mao, da o mesmo."""
    repo = _copia("misto", tmp_path)
    _rodar(repo, capsys)
    saida = repo / ".sparkforge" / "scan"
    plano = _core.scan(str(repo), dry_run=True)["plan"]
    uniao = []
    for entrada in sorted(plano["entries"], key=lambda e: (e["analyze"], e["path"])):
        from sparkforge.scan import Entrada

        uniao += _core._scan_extrair(
            Entrada(entrada["analyze"], entrada["path"], entrada["origin"],
                    entrada.get("job_name")), repo,
        )
    manual_facts = tmp_path / "manual_facts.json"
    manual_facts.write_text(json.dumps(uniao), encoding="utf-8")
    fundidos = _core.fuse_facts([str(manual_facts)], limit=None)["items"]
    manual = _core.judge_findings(facts=fundidos, limit=None)["items"]
    scan_findings = json.loads((saida / "findings.json").read_text(encoding="utf-8"))
    assert sorted(f["rule_id"] for f in scan_findings) == sorted(f["rule_id"] for f in manual)
    # O `facts.json` do scan e o conjunto que o `judge` a mao JULGOU: os
    # fundidos mais os facts da deteccao de runtime, que os SF-ENV-00x citam.
    _, julgados_a_mao = _core._runtime_e_facts(facts=_core._facts_from_dicts(fundidos))
    gravados = json.loads((saida / "facts.json").read_text(encoding="utf-8"))
    assert sorted(f["id"] for f in gravados) == sorted(f.id for f in julgados_a_mao)
    assert "SF-LF-005" in {f["rule_id"] for f in scan_findings}, "o fuse destrava o P0 de LF"


def test_dry_run_nao_grava(tmp_path, capsys):
    repo = _copia("misto", tmp_path)
    saida = _rodar(repo, capsys, "--dry-run")
    assert saida["dry_run"] is True and saida["plan"]["entries"]
    assert not (repo / ".sparkforge" / "scan").exists()


def test_sarif_igual_ao_report_github(tmp_path, capsys):
    """SC4: o SARIF do scan e o que `report github` escreve sobre os mesmos arquivos."""
    repo = _copia("misto", tmp_path)
    resumo = _rodar(repo, capsys, "--format", "sarif", "--fail-on", "P0", esperado=1)
    assert resumo["gate"]["tripped"] is True
    scan_dir = repo / ".sparkforge" / "scan"
    payload = _core.report_github(
        str(scan_dir / "findings.json"), str(scan_dir / "facts.json"), repo=str(repo),
        fail_on="P0",
    )
    textos = _core.report_github_textos(payload)
    for relativo in resumo["sarif"]["files"]:
        nome = Path(relativo).name
        assert (repo / relativo).read_text(encoding="utf-8") == textos[nome]


def test_analyze_que_falha_nao_derruba_os_outros(tmp_path, capsys):
    resumo = _rodar(_copia("analyze_falhou", tmp_path), capsys)
    assert resumo["refused_by_reason"] == {"analyze_falhou": 1}
    assert resumo["analyzes"]["pyspark"]["facts"] > 0


def test_repo_inexistente_sai_2(tmp_path):
    assert main(["scan", str(tmp_path / "nao_existe")]) == 2
