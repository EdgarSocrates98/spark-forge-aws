"""Golden do Knowledge Drift Radar (§17), de ponta a ponta pela CLI.

Cada caso de `fixtures/knowledge_drift/` e um lock SINTETICO apontado por
`SPARKFORGE_SOURCES_LOCK`; o catalogo, os documentos de `knowledge/`, os goldens,
os evals e os agentes sao os reais. O golden muda quando um golden, eval ou
agente novo passa a citar uma regra do impacto -- e e isso que ele deve
acusar.

Regenerar depois de mudanca DELIBERADA:
`SPARKFORGE_REGEN_DRIFT=1 pytest tests/test_fixtures_golden_knowledge_drift.py`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters.cli import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "knowledge_drift"
REGEN = os.environ.get("SPARKFORGE_REGEN_DRIFT") == "1"
CASOS = sorted(p.name for p in FIXTURES.iterdir() if (p / "meta.yaml").is_file())
LF = "https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html"


def _rodar(caso: str, monkeypatch, capsys) -> dict:
    meta = yaml.safe_load((FIXTURES / caso / "meta.yaml").read_text(encoding="utf-8"))
    monkeypatch.delenv("SPARKFORGE_PACKS", raising=False)
    monkeypatch.setenv("SPARKFORGE_SOURCES_LOCK", str(FIXTURES / caso / "lock.json"))
    assert main(["knowledge", "drift", "--as-of", "2026-09-13", *meta["args"]]) == 0
    return json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("caso", CASOS)
def test_golden(caso, monkeypatch, capsys):
    saida = _rodar(caso, monkeypatch, capsys)
    esperado = FIXTURES / caso / "expected" / "result.json"
    texto = json.dumps(saida, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if REGEN:
        esperado.parent.mkdir(parents=True, exist_ok=True)
        esperado.write_text(texto, encoding="utf-8", newline="\n")
    assert texto == esperado.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_lf_so_as_lidas_antes_da_mudanca_entram(monkeypatch, capsys):
    [fonte] = _rodar("lf_consideracoes", monkeypatch, capsys)["changed_sources"]
    for citacao in fonte["citations"]:
        antes = (citacao["retrieved"] or "") < "2026-09-09"
        assert (citacao["id"] in fonte["impact"]["rules"] + fonte["impact"]["docs"]) is antes
        assert (citacao["id"] in fonte["revalidated"]) is not antes
    assert fonte["impact"]["rules"] and fonte["revalidated"]


def test_lf_impacto_conferivel_por_arquivo(monkeypatch, capsys):
    [fonte] = _rodar("lf_consideracoes", monkeypatch, capsys)["changed_sources"]
    regras = set(fonte["impact"]["rules"])
    for golden in fonte["impact"]["goldens"]:
        achados = json.loads((ROOT / "fixtures" / golden / "expected" / "findings.json").read_text(
            encoding="utf-8"))
        assert regras & {a["rule_id"] for a in achados}, golden
    for arquivo in fonte["impact"]["evals"] + fonte["impact"]["agents"]:
        texto = (ROOT / arquivo).read_text(encoding="utf-8")
        assert any(r in texto or r.rsplit("-", 1)[0] in texto for r in regras), arquivo


def test_fixa_por_versao_nunca_entra(monkeypatch, capsys):
    assert _rodar("fixa_por_versao", monkeypatch, capsys)["changed_sources"] == []


def test_url_fora_do_lock_sai_2(monkeypatch, capsys):
    monkeypatch.setenv("SPARKFORGE_SOURCES_LOCK", str(FIXTURES / "nada_mudou" / "lock.json"))
    assert main(["knowledge", "drift", "--source", "https://nao.vigiada.invalid/"]) == 2


def test_lock_ausente_e_unresolved(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("SPARKFORGE_SOURCES_LOCK", str(tmp_path / "nao-existe.json"))
    assert main(["knowledge", "drift", "--as-of", "2026-09-13"]) == 0
    saida = json.loads(capsys.readouterr().out)
    assert saida["unresolved"][0]["field"] == "lock"


def test_sem_repositorio(monkeypatch, capsys):
    from sparkforge import knowledge_drift

    monkeypatch.setattr(knowledge_drift, "repo_root", lambda: None)
    saida = _rodar("lf_consideracoes", monkeypatch, capsys)
    assert {u["reason"] for u in saida["unresolved"]} == {"sem_repositorio"}
    assert saida["changed_sources"][0]["impact"]["goldens"] is None
    assert saida["changed_sources"][0]["url"] == LF
