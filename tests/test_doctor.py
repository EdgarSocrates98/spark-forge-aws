"""`sparkforge doctor`: cada status de cada checagem, o exit e a tool sem rede."""
from __future__ import annotations

import json

import pytest

from sparkforge import __version__
from sparkforge import doctor as dr
from sparkforge.adapters import _core
from sparkforge.adapters.cli import main


@pytest.fixture(autouse=True)
def home_isolado(tmp_path, monkeypatch):
    """O doctor le o manifesto do HOME: nenhum teste deste arquivo le o do operador."""
    casa = tmp_path / "home_isolado"
    casa.mkdir()
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.setenv("USERPROFILE", str(casa))
    monkeypatch.setenv("APPDATA", str(casa / "AppData" / "Roaming"))
    monkeypatch.setenv("CODEX_HOME", str(casa / ".codex"))
    return casa


INTEGRACOES = ["integracao_claude", "integracao_devin", "integracao_codex",
               "integracao_copilot"]
IDS = [
    "pacote", "extras", "mcp", "catalogo", "packs", "knowledge",
    "indice_de_codigo", "artefatos", "credencial_aws",
    "integracao_claude", "integracao_devin", "integracao_codex", "integracao_copilot",
]


def test_pacote():
    assert dr.avaliar_pacote("0.5.0", (3, 11, 0)).status == dr.OK
    assert dr.avaliar_pacote(None, (3, 11, 0)).status == dr.WARN
    assert dr.avaliar_pacote("0.5.0", (3, 9, 18)).status == dr.FAIL


def test_extras():
    assert dr.avaliar_extras({"mcp": True, "boto3": True, "pyarrow": True}).status == dr.OK
    faltando = dr.avaliar_extras({"mcp": True, "boto3": False, "pyarrow": False})
    assert faltando.status == dr.WARN
    assert faltando.unlock == 'pip install "sparkforge-aws[aws,parquet]"'


def test_mcp():
    assert dr.avaliar_mcp(False, None, None).status == dr.SKIP
    assert dr.avaliar_mcp(True, None, "ImportError: x").status == dr.FAIL
    assert dr.avaliar_mcp(True, 97, None).status == dr.OK


def test_catalogo():
    assert dr.avaliar_catalogo(None, "CatalogError: x").status == dr.FAIL
    assert dr.avaliar_catalogo(190, None).status == dr.OK


def test_packs():
    assert dr.avaliar_packs(None, "erro").status == dr.FAIL
    # `env` e o nome da variavel e vem sempre (medido: pack_list sem a variavel).
    vazio = {"env": "SPARKFORGE_PACKS", "active": [], "refused": []}
    assert dr.avaliar_packs(vazio, None).status == dr.SKIP
    recusado = {**vazio, "refused": [{"reason": "prefixo_reservado"}]}
    assert dr.avaliar_packs(recusado, None).status == dr.WARN
    assert dr.avaliar_packs({**vazio, "active": [{}]}, None).status == dr.OK


def test_knowledge():
    assert dr.avaliar_knowledge(None, "erro").status == dr.FAIL
    assert dr.avaliar_knowledge({"stale": 2, "fresh": 1}, None).status == dr.WARN
    assert dr.avaliar_knowledge({"aging": 4, "fixed": 15}, None).status == dr.OK


def test_indice_de_codigo():
    assert dr.avaliar_indice(None, "erro").status == dr.WARN
    assert dr.avaliar_indice({"initialized": False}, None).status == dr.SKIP
    assert dr.avaliar_indice({"initialized": True, "fresh": False}, None).status == dr.WARN
    assert dr.avaliar_indice({"initialized": True, "fresh": True}, None).status == dr.OK
    sem_conferir = dr.avaliar_indice({"initialized": True, "fresh": None}, None)
    assert sem_conferir.status == dr.OK and sem_conferir.unlock == "sparkforge code status --root ."


def test_doctor_nao_toca_o_indice_de_codigo(tmp_path):
    """Com indice existente, o doctor nao muda o banco (code_status mudaria)."""
    from sparkforge.adapters.cli import main as cli

    (tmp_path / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    assert cli(["code", "init", "--root", str(tmp_path)]) == 0
    banco = _core._code_banco(_core._code_raiz(str(tmp_path)), None)
    antes = banco.stat().st_mtime_ns
    [indice] = [c for c in _core.doctor(str(tmp_path))["checks"] if c["id"] == "indice_de_codigo"]
    assert indice["status"] == "ok"
    assert banco.stat().st_mtime_ns == antes


def test_artefatos():
    assert dr.avaliar_artefatos(None, "erro").status == dr.WARN
    assert dr.avaliar_artefatos({"total_count": 0}, None).status == dr.SKIP
    ruim = {"total_count": 2, "ok_count": 1, "missing_count": 1, "mismatched_count": 0}
    assert dr.avaliar_artefatos(ruim, None).status == dr.WARN
    bom = {"total_count": 1, "ok_count": 1, "missing_count": 0, "mismatched_count": 0}
    assert dr.avaliar_artefatos(bom, None).status == dr.OK


def test_credencial_aws():
    assert dr.avaliar_credencial(False, None, None, None, False).status == dr.SKIP
    assert dr.avaliar_credencial(True, None, None, None, False).status == dr.WARN
    assert dr.avaliar_credencial(True, "env", None, "ClientError: x", True).status == dr.WARN
    local = dr.avaliar_credencial(True, "shared-credentials-file", None, None, False)
    assert local.status == dr.OK and local.unlock == "sparkforge doctor --online"
    assert dr.avaliar_credencial(True, "env", "123456789012", None, True).status == dr.OK


def test_resumo_saudavel_so_sem_fail():
    ok = dr.resumo([dr.Checagem("a", dr.OK, ""), dr.Checagem("b", dr.WARN, "")], online=False)
    assert ok["healthy"] is True and ok["counts"]["warn"] == 1
    ruim = dr.resumo([dr.Checagem("a", dr.FAIL, "")], online=False)
    assert ruim["healthy"] is False




def test_doctor_de_verdade_tem_as_treze_checagens(tmp_path, home_isolado):
    assert len(IDS) == 13
    repo = tmp_path / "repo"
    repo.mkdir()
    saida = _core.doctor(str(repo))
    assert [c["id"] for c in saida["checks"]] == IDS
    assert saida["online"] is False
    assert list(repo.iterdir()) == [], "doctor nao grava nada no repositorio"


def test_cli_sai_1_com_catalogo_invalido(tmp_path, monkeypatch, capsys):
    vazio = tmp_path / "catalogo_vazio"
    vazio.mkdir()
    (vazio / "quebrado.yaml").write_text("- id: [nao fecha\n", encoding="utf-8")
    monkeypatch.setenv("SPARKFORGE_CATALOG", str(vazio))
    assert main(["doctor", "--repo", str(tmp_path)]) == 1
    saida = json.loads(capsys.readouterr().out)
    [catalogo] = [c for c in saida["checks"] if c["id"] == "catalogo"]
    assert catalogo["status"] == "fail" and catalogo["unlock"]


def test_cli_sai_0_sem_fail(tmp_path, home_isolado, capsys):
    assert main(["doctor", "--repo", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["healthy"] is True


def test_tool_nunca_recebe_online():
    from sparkforge.adapters.tools import TOOLS

    tool = TOOLS["sparkforge_doctor"]
    assert "online" not in (tool["inputSchema"].get("properties") or {})
    assert tool["annotations"]["openWorldHint"] is False
    assert tool["annotations"]["readOnlyHint"] is True


def test_repo_inexistente_sai_2(tmp_path):
    assert main(["doctor", "--repo", str(tmp_path / "nao_existe")]) == 2


def test_manifesto_ilegivel_mantem_uma_checagem_por_host(tmp_path, home_isolado):
    checagens = dr.avaliar_integracoes(None, "ManifestoRecusado: manifesto_ilegivel", None)
    assert [c.id for c in checagens] == INTEGRACOES
    assert {c.status for c in checagens} == {dr.WARN}
    assert all("manifesto_ilegivel" in c.detail for c in checagens)
    # O doctor de verdade, com o manifesto do HOME truncado, mantem os mesmos ids.
    manifesto = home_isolado / ".sparkforge" / "integrations.json"
    manifesto.parent.mkdir()
    manifesto.write_text('{"schema": 2, "files": {', encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    assert [c["id"] for c in _core.doctor(str(repo))["checks"]] == IDS


def test_versao_gravada_diferente_da_instalada_sai_warn():
    manifesto = {"hosts": {"devin": {"package_version": "0.0.1"}}, "files": {}}
    por_id = {c.id: c for c in dr.avaliar_integracoes(
        manifesto, None, None, installed="0.5.0")}
    devin = por_id["integracao_devin"]
    assert devin.status == dr.WARN
    assert "0.0.1" in devin.detail and "0.5.0" in devin.detail
    assert devin.unlock == "sparkforge integrate devin --scope user"
    igual = dr.avaliar_integracoes(manifesto, None, None, installed="0.0.1")
    assert {c.id: c.status for c in igual}["integracao_devin"] == dr.OK
    # O doctor de verdade compara com a versao do pacote que roda.
    assert __version__
