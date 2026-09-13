"""Golden do Forge Pack (§5), de ponta a ponta pela CLI.

`fixtures/packs/` tem o pack sintetico `acme-platform`, um pack por motivo de
recusa (`recusa_*`) e um pack valido cuja regra nunca dispara
(`check_regra_morta`). O golden de `pack list` roda com todos eles ativos ao
mesmo tempo -- e a prova de que um pack recusado nao derruba os outros.

Regenerar depois de mudanca DELIBERADA:
`SPARKFORGE_REGEN_PACKS=1 pytest tests/test_fixtures_golden_packs.py`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from sparkforge.adapters.cli import main
from sparkforge.adapters.tools import TOOLS
from sparkforge.packs import ENV, installed_version

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "packs"
REGEN = os.environ.get("SPARKFORGE_REGEN_PACKS") == "1"
ESPERADO = FIXTURES / "_expected" / "pack_list.json"
ATIVADOS = [FIXTURES / "acme-platform"] + sorted(
    p for p in FIXTURES.iterdir() if p.name.startswith("recusa_")
)


def _relativo(valor: str) -> str:
    return Path(valor).resolve().relative_to(ROOT).as_posix()


def _pack_list(monkeypatch, capsys) -> dict:
    monkeypatch.delenv("SPARKFORGE_SOURCES_LOCK", raising=False)
    monkeypatch.setenv(ENV, os.pathsep.join(str(p) for p in ATIVADOS))
    assert main(["pack", "list"]) == 0
    saida = json.loads(capsys.readouterr().out)
    for pack in saida["active"]:
        pack["dir"] = _relativo(pack["dir"])
    for recusa in saida["refused"]:
        recusa["dir"] = _relativo(recusa["dir"])
        recusa["detail"] = recusa["detail"].replace(installed_version() or "", "<core>")
    saida["installed_core"] = "<core>"
    return saida


def test_golden_pack_list(monkeypatch, capsys):
    texto = json.dumps(_pack_list(monkeypatch, capsys), ensure_ascii=False, indent=2) + "\n"
    if REGEN:
        ESPERADO.parent.mkdir(parents=True, exist_ok=True)
        ESPERADO.write_text(texto, encoding="utf-8", newline="\n")
    assert texto == ESPERADO.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_toda_recusa_do_schema_tem_pack_de_fixture(monkeypatch, capsys):
    saida = _pack_list(monkeypatch, capsys)
    schema = TOOLS["sparkforge_pack_list"]["outputSchema"]
    ramo = next(r for r in schema["oneOf"] if "refused" in r.get("properties", {}))
    motivos = set(ramo["properties"]["refused"]["items"]["properties"]["reason"]["enum"])
    assert {r["reason"] for r in saida["refused"]} == motivos


def test_pack_check_verde(monkeypatch, capsys):
    monkeypatch.delenv(ENV, raising=False)
    assert main(["pack", "check", str(FIXTURES / "acme-platform")]) == 0
    saida = json.loads(capsys.readouterr().out)
    assert [c["fired"] for c in saida["cases"]] == [["ACME-GOV-002"], ["ACME-GOV-001"]]


def test_pack_check_vermelho_nomeia_a_regra(monkeypatch, capsys):
    monkeypatch.delenv(ENV, raising=False)
    assert main(["pack", "check", str(FIXTURES / "check_regra_morta")]) == 1
    saida = json.loads(capsys.readouterr().out)
    assert saida["rules_without_fixture"] == ["MORTA-GOV-001"] and saida["ok"] is False


def test_pack_check_de_pack_recusado_sai_1(monkeypatch, capsys):
    monkeypatch.delenv(ENV, raising=False)
    assert main(["pack", "check", str(FIXTURES / "recusa_prefixo_reservado")]) == 1
    assert json.loads(capsys.readouterr().out)["refused"]["reason"] == "prefixo_reservado"
