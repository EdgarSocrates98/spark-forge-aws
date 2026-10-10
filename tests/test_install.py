"""`sparkforge-aws install|status|repair|uninstall` nos escopos project/workspace.

Cada teste instala num `tmp_path/projeto` e aponta HOME/APPDATA para um home
isolado: nada toca o HOME real. O escopo `user` e o integrate ja cobertos por
test_integrate.py; aqui vale o que e novo — o ciclo de vida no repositorio.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge_aws import _installkit as kit
from sparkforge_aws.install import lifecycle

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _home_isolado(tmp_path, monkeypatch):
    casa = tmp_path / "home_padrao"
    casa.mkdir()
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.setenv("USERPROFILE", str(casa))
    monkeypatch.setenv("APPDATA", str(casa / "AppData" / "Roaming"))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    from sparkforge_aws.integrate import claude as _claude
    monkeypatch.setattr(_claude, "WHICH_PADRAO", lambda _nome: None)
    monkeypatch.setattr(_claude, "RUNNER_PADRAO", lambda _a: None)


@pytest.fixture()
def projeto(tmp_path):
    p = tmp_path / "projeto"
    p.mkdir()
    (p / ".git").mkdir()
    return p


def _arquivos(base: Path) -> list[str]:
    return sorted(
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )


# --------------------------------------------------------------------------
# install
# --------------------------------------------------------------------------

def test_install_requer_aprovacao_ou_dry_run(projeto):
    with pytest.raises(kit.InstallError) as exc:
        lifecycle.install("devin", scope="project", root=projeto)
    assert exc.value.kind == kit.E_NOTAPPROVED
    assert _arquivos(projeto) == [".git/.keep"] or not any(
        p.is_file() for p in projeto.rglob("*") if ".git" not in p.parts)


def test_install_project_devin_escreve_mirrors_e_mcp(projeto):
    out = lifecycle.install("devin", scope="project", root=projeto, yes=True)
    assert out["status"] == "completed"
    assert out["verification"]["status"] == "PASS"
    paths = {f["path"] for f in out["managed_files"]}
    assert any(p.startswith(".devin/skills/") for p in paths)
    assert any(p.startswith(".agents/skills/") for p in paths)
    mcp = json.loads((projeto / ".mcp.json").read_text(encoding="utf-8"))
    assert "sparkforge-aws" in mcp["mcpServers"]
    assert "sparkforge-aws:managed" in (projeto / "AGENTS.md").read_text(
        encoding="utf-8")
    receipts = list((projeto / ".sparkforge_aws" / "receipts").glob("install-*.json"))
    assert receipts and json.loads(receipts[0].read_text())["schema"] == kit.SCHEMA_RECEIPT


def test_install_profile_minimal_sem_mirrors(projeto):
    out = lifecycle.install("devin", scope="project", root=projeto,
                            profile="minimal", yes=True)
    assert out["status"] == "completed"
    assert out["managed_files"] == []
    assert (projeto / ".mcp.json").exists()
    assert not (projeto / ".devin").exists()


def test_install_profile_full_inclui_agents(projeto):
    out = lifecycle.install("devin", scope="project", root=projeto,
                            profile="full", yes=True)
    paths = {f["path"] for f in out["managed_files"]}
    assert any(p.startswith(".devin/agents/") for p in paths)


def test_install_nao_sobrescreve_arquivo_do_usuario(projeto):
    skill = projeto / ".devin" / "skills"
    skill.mkdir(parents=True)
    alvo = None
    plano = lifecycle.install("devin", scope="project", root=projeto,
                              dry_run=True)
    primeiro = next(f["path"] for f in plano["managed_files"]
                    if f["path"].startswith(".devin/skills/")
                    and f["path"].endswith("SKILL.md"))
    alvo = projeto / primeiro
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text("conteudo do usuario", encoding="utf-8")
    out = lifecycle.install("devin", scope="project", root=projeto, yes=True)
    assert alvo.read_text(encoding="utf-8") == "conteudo do usuario"
    assert out["status"] == "failed" or out.get("refused")


def test_install_dry_run_nao_escreve(projeto):
    out = lifecycle.install("devin", scope="project", root=projeto, dry_run=True)
    assert out["status"] == "planned"
    assert not (projeto / ".devin").exists()
    assert not (projeto / ".mcp.json").exists()


def test_install_workspace_scope(projeto):
    (projeto / "pyproject.toml").write_text("[tool.forge.workspace]\n",
                                            encoding="utf-8")
    out = lifecycle.install("devin", scope="workspace", root=projeto, yes=True)
    assert out["status"] == "completed"
    assert (projeto / ".sparkforge_aws" / "workspace-install.json").exists()


def test_install_host_desconhecido_recusa(projeto):
    with pytest.raises(kit.InstallError) as exc:
        lifecycle.install("cursor", scope="project", root=projeto, yes=True)
    assert exc.value.kind == kit.E_HOST


# --------------------------------------------------------------------------
# status / doctor / repair
# --------------------------------------------------------------------------

def test_status_healthy_e_drift(projeto):
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    st = lifecycle.status(scope="project", root=projeto)
    assert st["status"] == "healthy"
    assert st["drift"]["ok"] == st["ledger_entries"] > 0

    alvo = projeto / st["hosts"]["devin"][0]
    alvo.write_text("edicao manual", encoding="utf-8")
    st2 = lifecycle.status(scope="project", root=projeto)
    assert st2["status"] == "degraded"
    assert st2["drift"]["modified"]


def test_status_sem_instalacao_e_unverified(projeto):
    st = lifecycle.status(scope="project", root=projeto)
    assert st["status"] == "unverified"
    assert st["ledger_entries"] == 0


def test_repair_restaura_asset_removido(projeto):
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    st = lifecycle.status(scope="project", root=projeto)
    vitima = projeto / st["hosts"]["devin"][0]
    original = vitima.read_bytes()
    vitima.unlink()
    rep = lifecycle.repair(scope="project", root=projeto)
    assert rep["status"] == "completed"
    assert vitima.read_bytes() == original


def test_repair_nao_toca_em_arquivo_do_usuario(projeto):
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    meu = projeto / "meu_arquivo.txt"
    meu.write_text("meu", encoding="utf-8")
    lifecycle.repair(scope="project", root=projeto)
    assert meu.read_text(encoding="utf-8") == "meu"


# --------------------------------------------------------------------------
# uninstall
# --------------------------------------------------------------------------

def test_uninstall_reverte_tudo_menos_estado(projeto):
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    antes = {p for p in _arquivos(projeto) if not p.startswith(".git/")}
    assert antes - {".sparkforge_aws/integrations.json"} | {"AGENTS.md"}
    un = lifecycle.uninstall(scope="project", host="all", root=projeto,
                             purge=True)
    assert un["status"] == "completed"
    resto = [p for p in _arquivos(projeto) if not p.startswith(".git/")]
    assert resto == []
    assert not (projeto / ".devin").exists()
    assert not (projeto / ".agents").exists()
    assert not (projeto / ".mcp.json").exists()
    assert not (projeto / ".sparkforge_aws").exists()


def test_uninstall_preserva_conteudo_do_usuario(projeto):
    ag = projeto / "AGENTS.md"
    ag.write_text("# Meu projeto\n", encoding="utf-8")
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    lifecycle.uninstall(scope="project", host="all", root=projeto, purge=True)
    assert ag.read_text(encoding="utf-8").strip() == "# Meu projeto"


def test_uninstall_sem_instalacao_e_idempotente(projeto):
    un = lifecycle.uninstall(scope="project", host="all", root=projeto)
    assert un["status"] == "completed"
    assert un.get("removed", []) == [] or un["removed"] == []


# --------------------------------------------------------------------------
# update / mcp verify / CLI
# --------------------------------------------------------------------------

def test_update_rejeita_latest():
    out = lifecycle.update(to="latest")
    assert out["status"] == "failed"
    assert out["checks"][0]["status"] == "FAIL"


def test_update_sem_manifesto_bloqueia():
    out = lifecycle.update()
    assert out["status"] == "failed"
    assert out["checks"][0]["status"] == "BLOCKED"


def test_mcp_verify_documento():
    out = lifecycle.mcp_verify()
    assert out["id"] == "mcp-handshake"
    assert out["status"] in ("PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE",
                             "UNVERIFIED")


def test_cli_dispatch_install_dry_run(projeto, capsys, monkeypatch):
    monkeypatch.chdir(projeto)
    from sparkforge_aws.adapters import cli
    code = cli.main(["install", "--host", "devin", "--dry-run"])
    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["status"] == "planned"


def test_cli_dispatch_status(projeto, capsys, monkeypatch):
    monkeypatch.chdir(projeto)
    from sparkforge_aws.adapters import cli
    code = cli.main(["status"])
    assert code in (0, 1)
    doc = json.loads(capsys.readouterr().out)
    assert doc["forge_id"] == "spark-forge-aws"


def test_cli_erro_estruturado_sem_traceback(projeto, capsys, monkeypatch):
    monkeypatch.chdir(projeto)
    from sparkforge_aws.adapters import cli
    code = cli.main(["install", "--host", "devin"])
    assert code == 1
    doc = json.loads(capsys.readouterr().out)
    assert doc["error"]["kind"].endswith("NOT-APPROVED") or \
        "NOT-APPROVED" in json.dumps(doc)

def test_hosts_for_none_e_csv():
    """GAP-003: `none` nunca vira `all`; csv subconjunto e validado."""
    from sparkforge_aws.install.lifecycle import _hosts_for
    import pytest
    assert _hosts_for("all")
    assert _hosts_for("none") == []
    assert _hosts_for("") == []
    assert _hosts_for("claude") == ["claude"]
    assert set(_hosts_for("claude,devin")) == {"claude", "devin"}
    with pytest.raises(Exception):
        _hosts_for("nope")
