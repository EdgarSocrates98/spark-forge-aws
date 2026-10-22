"""`sparkforge-aws install|status|repair|uninstall` nos escopos project/workspace.

Cada teste instala num `tmp_path/projeto` e aponta HOME/APPDATA para um home
isolado: nada toca o HOME real. O escopo `user` e o integrate ja cobertos por
test_integrate.py; aqui vale o que e novo — o ciclo de vida no repositorio.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sparkforge_aws import _installkit as kit
from sparkforge_aws.install import lifecycle
from sparkforge_aws.ui import wizard

ROOT = Path(__file__).resolve().parents[1]


def test_fresh_directory_hides_repository_scope(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ctx = wizard.UIContext(interactive=False, color=False, unicode=False, width=80)
    assert wizard._scope_choices(ctx) == ["workspace", "user"]
    assert "No repository detected" in capsys.readouterr().out


def test_install_accepts_canonical_host_keyword(tmp_path):
    receipt = lifecycle.install(
        host="none", scope="workspace", root=tmp_path, dry_run=True,
    )
    assert receipt["status"] == "planned"


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
    assert "forge:spark-forge-aws:begin" in (projeto / "AGENTS.md").read_text(
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


def test_install_profile_recommended_inclui_agents(projeto):
    out = lifecycle.install("devin", scope="project", root=projeto,
                            profile="recommended", yes=True)
    paths = {f["path"] for f in out["managed_files"]}
    assert any(p.startswith(".devin/skills/") for p in paths)
    assert any(p.startswith(".devin/agents/") for p in paths)


def test_install_components_control_asset_kinds(projeto):
    out = lifecycle.install("devin", scope="project", root=projeto,
                            components=("skills",), yes=True)
    paths = {f["path"] for f in out["managed_files"]}
    assert any(p.startswith(".devin/skills/") for p in paths)
    assert not any(p.startswith(".devin/agents/") for p in paths)
    assert not (projeto / ".mcp.json").exists()


def test_install_host_all_mcp_compartilhado_sem_recusa(projeto):
    out = lifecycle.install("all", scope="project", root=projeto, yes=True)
    assert out["status"] == "completed"
    assert not out.get("refused")
    mcp = json.loads((projeto / ".mcp.json").read_text(encoding="utf-8"))
    entrada = mcp["mcpServers"]["sparkforge-aws"]
    assert set(entrada) == {"command", "args"}
    # o arquivo e um so: um unico registro no manifesto, sob um unico host
    manifesto = json.loads(
        (projeto / ".sparkforge_aws" / "integrations.json").read_text(
            encoding="utf-8"))
    donos = [h for h, r in manifesto["hosts"].items()
             if any(c["path"] == ".mcp.json" for c in r.get("config") or [])]
    assert len(donos) == 1


def test_install_host_all_idempotente(projeto):
    lifecycle.install("all", scope="project", root=projeto, yes=True)
    out = lifecycle.install("all", scope="project", root=projeto, yes=True)
    assert out["status"] == "completed"
    assert not out.get("refused")


def test_install_subset_depois_de_all_reconhece_mcp_gerenciado(projeto):
    lifecycle.install("all", scope="project", root=projeto, yes=True)
    out = lifecycle.install("copilot", scope="project", root=projeto,
                            yes=True)
    assert out["status"] == "completed"
    assert not out.get("refused")


def test_install_mcp_json_do_usuario_recusa(projeto):
    (projeto / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"sparkforge-aws": {
            "command": "outro", "args": []}}}),
        encoding="utf-8")
    out = lifecycle.install("claude", scope="project", root=projeto, yes=True)
    assert out["status"] == "failed" or out.get("refused")


def test_status_detecta_mcp_json_ausente(projeto):
    lifecycle.install("all", scope="project", root=projeto, yes=True)
    (projeto / ".mcp.json").unlink()
    st = lifecycle.status(scope="project", root=projeto)
    assert st["status"] != "healthy"
    assert ".mcp.json" in [d["path"] for d in st["drift"]["missing"]]


def test_status_detecta_mcp_json_entrada_editada(projeto):
    lifecycle.install("all", scope="project", root=projeto, yes=True)
    doc = json.loads((projeto / ".mcp.json").read_text(encoding="utf-8"))
    doc["mcpServers"]["sparkforge-aws"]["args"] = ["--adulterado"]
    (projeto / ".mcp.json").write_text(json.dumps(doc), encoding="utf-8")
    st = lifecycle.status(scope="project", root=projeto)
    assert ".mcp.json" in [d["path"] for d in st["drift"]["modified"]]


def test_repair_restaura_mcp_json_ausente(projeto):
    lifecycle.install("all", scope="project", root=projeto, yes=True)
    (projeto / ".mcp.json").unlink()
    rep = lifecycle.repair(scope="project", root=projeto)
    assert ".mcp.json" in rep["repaired"]
    doc = json.loads((projeto / ".mcp.json").read_text(encoding="utf-8"))
    assert "sparkforge-aws" in doc["mcpServers"]
    st = lifecycle.status(scope="project", root=projeto)
    assert st["status"] == "healthy"


def test_repair_nao_regrava_entrada_editada(projeto):
    lifecycle.install("all", scope="project", root=projeto, yes=True)
    doc = json.loads((projeto / ".mcp.json").read_text(encoding="utf-8"))
    doc["mcpServers"]["sparkforge-aws"]["args"] = ["--adulterado"]
    (projeto / ".mcp.json").write_text(json.dumps(doc), encoding="utf-8")
    rep = lifecycle.repair(scope="project", root=projeto)
    assert ".mcp.json" in rep["skipped"]
    doc2 = json.loads((projeto / ".mcp.json").read_text(encoding="utf-8"))
    assert doc2["mcpServers"]["sparkforge-aws"]["args"] == ["--adulterado"]


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
    assert not (projeto / ".sparkforge_aws").exists()


def test_install_doctor_receipt_uses_string_health_status(projeto):
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    health = lifecycle.doctor(scope="project", root=projeto)
    assert isinstance(health["status"], str)
    assert health["status"] in {"healthy", "degraded", "broken", "unverified"}


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
    # drift conta files + configs gerenciados (.mcp.json); ledger so files
    manifesto = json.loads(
        (projeto / ".sparkforge_aws" / "integrations.json").read_text(
            encoding="utf-8"))
    configs = len({c["path"]
                   for r in manifesto["hosts"].values()
                   for c in r.get("config") or []})
    assert st["drift"]["ok"] == st["ledger_entries"] + configs > 0

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
    # `.forge/context/` e shared workspace state (ownership `shared`), nao
    # state deste forge: uninstall so desregistra a propria entrada.
    assert sorted(resto) == [
        ".forge/context/ROUTING.md",
        ".forge/context/registry.json",
    ]
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


def test_mcp_serve_delega_transporte_e_modo(monkeypatch):
    from sparkforge_aws.adapters import mcp
    from sparkforge_aws.install import cli as install_cli

    recebido = []
    monkeypatch.setattr(mcp, "main", lambda argv: recebido.append(argv) or 0)
    out = install_cli._mcp_serve(SimpleNamespace(
        transport="stdio", mode="compact", host="127.0.0.1", port=9876))

    assert recebido == [[
        "--transport", "stdio", "--mode", "compact",
        "--host", "127.0.0.1", "--port", "9876",
    ]]
    assert out["status"] == "completed"


def test_mcp_serve_declara_comando_na_ajuda(capsys):
    from sparkforge_aws.adapters import cli

    with pytest.raises(SystemExit) as exc:
        cli.main(["mcp", "serve", "--help"])
    assert exc.value.code == 0
    assert "--transport {stdio,http}" in capsys.readouterr().out


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


def test_bare_install_tty_enters_guided_wizard(monkeypatch):
    from sparkforge_aws.adapters import cli
    from sparkforge_aws.install import cli as install_cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(install_cli, "run_guided_install", lambda: 17)
    assert cli.main(["install"]) == 17


def test_bare_install_non_tty_never_mutates(projeto, capsys, monkeypatch):
    from sparkforge_aws.adapters import cli

    monkeypatch.chdir(projeto)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: False)
    before = _arquivos(projeto)
    assert cli.main(["install"]) != 0
    assert _arquivos(projeto) == before
    output = capsys.readouterr().out.lower()
    assert "not-approved" in output or "escreve no projeto" in output


def test_explicit_install_flags_bypass_guided_wizard(projeto, capsys, monkeypatch):
    from sparkforge_aws.adapters import cli
    from sparkforge_aws.install import cli as install_cli

    monkeypatch.chdir(projeto)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(install_cli, "run_guided_install",
                        lambda: pytest.fail("explicit flags entered wizard"))
    assert cli.main(["install", "--dry-run", "--host", "devin"]) == 0
    assert "PLANNED" in capsys.readouterr().out


def test_guided_wizard_separates_gateway_profile_and_verifies_health(monkeypatch):
    from sparkforge_aws.ui import wizard

    monkeypatch.setattr(wizard, "env_check_rows", lambda: [])
    selects = iter([0, 0, 2])
    monkeypatch.setattr(wizard, "select", lambda *args, **kwargs: next(selects))
    multi = iter([{0, 1, 2}, {0}])
    monkeypatch.setattr(wizard, "multi_select", lambda *args, **kwargs: next(multi))
    monkeypatch.setattr(wizard, "confirm", lambda *args, **kwargs: True)
    calls = []

    def install_fn(**kwargs):
        calls.append(kwargs)
        return {"status": "planned" if kwargs["dry_run"] else "completed"}

    assert wizard.run_wizard(
        forge_name="sparkforge-aws",
        install_fn=install_fn,
        doctor_fn=lambda **_: {"status": "healthy"},
        ctx=wizard.UIContext(interactive=True, color=False, unicode=False, width=80),
    ) == 0
    assert [call["gateway_profile"] for call in calls] == ["deep", "deep"]


def test_guided_wizard_cancel_before_apply_returns_130(monkeypatch):
    from sparkforge_aws.ui import wizard

    monkeypatch.setattr(wizard, "env_check_rows", lambda: [])
    selects = iter([0, 0, 1])
    monkeypatch.setattr(wizard, "select", lambda *args, **kwargs: next(selects))
    multi = iter([{0, 1}, {0}])
    monkeypatch.setattr(wizard, "multi_select", lambda *args, **kwargs: next(multi))
    monkeypatch.setattr(wizard, "confirm", lambda *args, **kwargs: False)
    calls = []
    assert wizard.run_wizard(
        forge_name="sparkforge-aws",
        install_fn=lambda **kwargs: calls.append(kwargs) or {"status": "planned"},
        ctx=wizard.UIContext(interactive=True, color=False, unicode=False, width=80),
    ) == 130
    assert len(calls) == 1
    assert calls[0]["dry_run"] is True

def test_hosts_for_none_e_csv():
    """GAP-003: `none` nunca vira `all`; csv subconjunto e validado."""
    import pytest

    from sparkforge_aws.install.lifecycle import _hosts_for
    assert _hosts_for("all")
    assert _hosts_for("none") == []
    assert _hosts_for("") == []
    assert _hosts_for("claude") == ["claude"]
    assert set(_hosts_for("claude,devin")) == {"claude", "devin"}
    with pytest.raises(kit.InstallError):
        _hosts_for("nope")


# --------------------------------------------------------------------------
# forge/context/v1 — registry de workspace (install-2.0 ciclo 2)
# --------------------------------------------------------------------------


def test_install_escreve_forge_context(projeto):
    from sparkforge_aws import _forgecontext as fctx

    out = lifecycle.install("devin", scope="project", root=projeto, yes=True)
    assert out["status"] == "completed"
    check = next(c for c in out["checks"] if c["id"] == "context-registry")
    assert check["status"] == "PASS"

    ctx = projeto / ".forge" / "context"
    registry = json.loads((ctx / "registry.json").read_text(encoding="utf-8"))
    assert registry["schema"] == "forge/context-registry/v1"
    entry = next(e for e in registry["forges"] if e["forge_id"] == "spark-forge-aws")
    assert entry["scope"] == "project"

    manifest = json.loads(
        (ctx / "capabilities" / "spark-forge-aws.json").read_text(encoding="utf-8")
    )
    assert manifest["schema"] == "forge/context/v1"
    assert manifest["forge_id"] == "spark-forge-aws"
    assert fctx.validate_manifest(manifest) == []
    assert manifest["skills"], "manifesto sem skills reais"
    assert manifest["rule_areas"], "manifesto sem rule areas"
    assert manifest["knowledge_providers"], "manifesto sem knowledge provider"
    assert manifest["integrity"]["files"]["forge.json"].startswith("sha256:")

    routing = (ctx / "ROUTING.md").read_text(encoding="utf-8")
    assert "spark-forge-aws" in routing
    assert "aws-glue" in routing


def test_install_context_idempotente_byte_a_byte(projeto):
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    ctx = projeto / ".forge" / "context"
    snap = {
        p.relative_to(ctx).as_posix(): p.read_bytes()
        for p in sorted(ctx.rglob("*"))
        if p.is_file()
    }
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    depois = {
        p.relative_to(ctx).as_posix(): p.read_bytes()
        for p in sorted(ctx.rglob("*"))
        if p.is_file()
    }
    assert snap == depois


def test_uninstall_desregistra_so_o_proprio_forge(projeto):
    from sparkforge_aws import _forgecontext as fctx

    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    estrangeiro = fctx.build_manifest(
        forge_id="forge-alheia",
        name="Forge Alheia",
        version="1.0.0",
        cli="forge-alheia",
        package="forge_alheia",
        distribution="forge-alheia",
        python_spec=">=3.10",
        scope="project",
        domains=("dominio-alheio",),
        skills=("skill-alheia",),
    )
    fctx.register_forge(projeto, estrangeiro, owner="forge-alheia")

    un = lifecycle.uninstall(scope="project", host="all", root=projeto, purge=True)
    assert un["status"] == "completed"

    ctx = projeto / ".forge" / "context"
    registry = json.loads((ctx / "registry.json").read_text(encoding="utf-8"))
    ids = {e["forge_id"] for e in registry["forges"]}
    assert ids == {"forge-alheia"}
    assert not (ctx / "capabilities" / "spark-forge-aws.json").exists()
    assert (ctx / "capabilities" / "forge-alheia.json").exists()
    routing = (ctx / "ROUTING.md").read_text(encoding="utf-8")
    assert "forge-alheia" in routing
    assert "spark-forge-aws" not in routing


# --------------------------------------------------------------------------
# consumer docs — install-2.0 ciclo 3 (lf-0036)
# --------------------------------------------------------------------------


def test_install_escreve_consumer_docs(projeto):
    """Workspace vazio recebe os 3 docs + registry + routing + manifesto."""
    out = lifecycle.install("devin", scope="project", root=projeto, yes=True)
    assert out["status"] == "completed"
    check = next(c for c in out["checks"] if c["id"] == "consumer-docs")
    assert check["status"] == "PASS"

    agents = (projeto / "AGENTS.md").read_text(encoding="utf-8")
    claude = (projeto / "CLAUDE.md").read_text(encoding="utf-8")
    proto = (projeto / "AGENT_PROTOCOL.md").read_text(encoding="utf-8")

    assert "<!-- forge:ecosystem:begin -->" in agents
    assert "<!-- forge:spark-forge-aws:begin -->" in agents
    assert "@AGENTS.md" in claude
    for sec in (
        "1. Discovery", "2. Classification", "3. Routing",
        "4. Context Retrieval", "5. Planning", "6. Execution",
        "7. Evaluation", "8. Verification", "9. Reporting",
    ):
        assert sec in proto
    assert proto.startswith("<!-- forge:agent-protocol:v1 -->")
    assert ".forge/context/registry.json" in proto


def test_install_preserva_conteudo_do_usuario_nos_docs(projeto):
    (projeto / "AGENTS.md").write_text("# Minhas regras\n\nTexto do usuario.\n",
                                       encoding="utf-8")
    (projeto / "CLAUDE.md").write_text("# Notas claude\n", encoding="utf-8")
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    agents = (projeto / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.startswith("# Minhas regras\n\nTexto do usuario.\n")
    assert "forge:spark-forge-aws:begin" in agents
    assert (projeto / "CLAUDE.md").read_text(encoding="utf-8").startswith(
        "# Notas claude\n")


def test_install_docs_idempotente_byte_a_byte(projeto):
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    nomes = ("AGENTS.md", "CLAUDE.md", "AGENT_PROTOCOL.md")
    snap = {n: (projeto / n).read_bytes() for n in nomes}
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    assert {n: (projeto / n).read_bytes() for n in nomes} == snap


def test_dois_forges_blocos_independentes_protocolo_compartilhado(projeto):
    from sparkforge_aws import _forgecontext as fctx

    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    alheio = fctx.build_manifest(
        forge_id="forge-alheia", name="Forge Alheia", version="1.0.0",
        cli="forge-alheia", package="forge_alheia", distribution="forge-alheia",
        python_spec=">=3.10", scope="project", domains=("dominio-alheio",),
        skills=("skill-alheia",),
    )
    fctx.register_forge(projeto, alheio, owner="forge-alheia")
    fctx.install_docs(projeto, alheio, owner="forge-alheia")

    agents = (projeto / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.count("forge:ecosystem:begin") == 1
    assert "forge:spark-forge-aws:begin" in agents
    assert "forge:forge-alheia:begin" in agents
    proto = (projeto / "AGENT_PROTOCOL.md").read_text(encoding="utf-8")
    assert "forge:spark-forge-aws:begin" in proto
    assert "forge:forge-alheia:begin" in proto

    # uninstall seletivo: some so o nosso, protocolo continua compartilhado
    lifecycle.uninstall(scope="project", host="all", root=projeto, purge=True)
    agents = (projeto / "AGENTS.md").read_text(encoding="utf-8")
    assert "forge:spark-forge-aws" not in agents
    assert "forge:forge-alheia:begin" in agents
    proto = (projeto / "AGENT_PROTOCOL.md").read_text(encoding="utf-8")
    assert "forge:forge-alheia:begin" in proto
    assert "spark-forge-aws" not in proto


def test_install_recusa_marcador_ambiguo(projeto):
    (projeto / "AGENTS.md").write_text(
        "# x\n<!-- forge:spark-forge-aws:begin -->\na\n"
        "<!-- forge:spark-forge-aws:begin -->\nb\n"
        "<!-- forge:spark-forge-aws:end -->\n",
        encoding="utf-8")
    out = lifecycle.install("devin", scope="project", root=projeto, yes=True)
    check = next(
        (c for c in out["checks"] if c["id"] == "consumer-docs"), None)
    assert check is not None and check["status"] == "BLOCKED"
    assert "FORGE-CONTEXT-CONFLICT" in check["detail"]


def test_install_recusa_protocolo_estrangeiro(projeto):
    (projeto / "AGENT_PROTOCOL.md").write_text("# protocolo do usuario\n",
                                               encoding="utf-8")
    out = lifecycle.install("devin", scope="project", root=projeto, yes=True)
    check = next(
        (c for c in out["checks"] if c["id"] == "consumer-docs"), None)
    assert check is not None and check["status"] == "BLOCKED"
    assert "FORGE-CONTEXT-CONFLICT" in check["detail"]
    assert (projeto / "AGENT_PROTOCOL.md").read_text(
        encoding="utf-8") == "# protocolo do usuario\n"


def test_repair_reconstroi_bloco_danificado(projeto):
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    alvo = projeto / "AGENTS.md"
    alvo.write_text(
        alvo.read_text(encoding="utf-8").replace("Spark Forge AWS", "ADULTERADO"),
        encoding="utf-8")
    rep = lifecycle.repair(scope="project", root=projeto)
    assert rep["status"] in ("completed", "failed")
    assert "ADULTERADO" not in alvo.read_text(encoding="utf-8")


def test_skill_instalada_referencia_protocolo_existente(projeto):
    """Refs a AGENT_PROTOCOL.md em assets instalados devem resolver (lf-0034)."""
    lifecycle.install("devin", scope="project", root=projeto, yes=True)
    refs = 0
    for skill in projeto.rglob("SKILL.md"):
        if "AGENT_PROTOCOL.md" in skill.read_text(encoding="utf-8"):
            refs += 1
    if refs:
        assert (projeto / "AGENT_PROTOCOL.md").exists()
