"""`sparkforge-aws portal` — adapter forge/PortalApi/1 sobre os serviços reais.

Cada teste sobe o servidor do portal contra um `tmp_path/projeto` com HOME
isolada: nada toca o HOME real nem o checkout. O catálogo (skills/agents) vem
do repo da forja — é o que a instalação entrega, independente do workspace.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from sparkforge_aws import portal_adapter as pa


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


@pytest.fixture()
def server(projeto):
    srv = pa.build_server(projeto)
    srv.serve_in_thread()
    yield srv
    srv.shutdown()
    srv.server_close()


def _call(srv, method: str, path: str, body: dict | None = None,
          session: str | None = None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{srv.port}/api/v1{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Forge-Session": session or srv.session_token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 — 127.0.0.1 loopback
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ---------------------------------------------------------------------------
# bootstrap / health / catálogos
# ---------------------------------------------------------------------------

def test_bootstrap_workspace_vazio(server):
    code, env = _call(server, "GET", "/bootstrap")
    assert code == 200
    d = env["data"]["descriptor"]
    assert d["forge_id"] == "spark-forge-aws"
    assert env["schema"] == "forge/PortalApi/1"
    assert {c["id"] for c in d["capabilities"]} >= {
        "install", "hosts", "mcp", "skills", "agents", "tasks",
    }
    # sem ledger: honesto NOT_INSTALLED, nunca VERIFIED
    assert env["data"]["health"]["state"] == "NOT_INSTALLED"


def test_bootstrap_exige_sessao(server):
    code, env = _call(server, "GET", "/bootstrap", session="token-errado")
    assert code == 403


def test_catalogo_skills_e_agents_do_repo(server):
    code, env = _call(server, "GET", "/skills")
    assert code == 200
    assert len(env["data"]) >= 50
    assert all(s["state"] == "available" for s in env["data"])
    code, env = _call(server, "GET", "/agents")
    assert code == 200
    assert len(env["data"]) >= 15
    primeiro = env["data"][0]
    assert primeiro["id"] and primeiro["name"]


def test_hosts_observe_sem_binario(server):
    # WHICH_PADRAO stubbed → nenhum host detectado; unverified, nunca inventado
    code, env = _call(server, "GET", "/hosts")
    assert code == 200
    assert len(env["data"]) == 4
    assert all(h["detected"] is False for h in env["data"])


def test_hosts_launch_host_ausente_recusa_nomeada(server):
    code, env = _call(server, "POST", "/hosts/launch", {"host": "devin"})
    assert code == 200
    assert env["data"]["refusal"] == "PORTAL-HOST-ABSENT"
    code, env = _call(server, "POST", "/hosts/launch", {"host": "emacs"})
    assert code == 400
    assert env["error"]["code"] == "PORTAL-BAD-FIELD"


def test_graph_sem_indice_recusa_com_unlock(server):
    code, env = _call(server, "GET", "/graphs")
    assert code == 200
    avail = env["data"]["availability"]
    assert avail["state"] == "no_graph"
    assert avail["unlock"]


# ---------------------------------------------------------------------------
# install lifecycle — plan → confirm → apply → health
# ---------------------------------------------------------------------------

def test_install_plan_apply_verified(server, projeto):
    code, env = _call(server, "POST", "/installation/plan",
                      {"scope": "project", "host": "devin", "profile": "minimal"})
    assert code == 200
    plan = env["data"]["plan"]
    token = env["data"]["plan_token"]
    assert plan["host"] == "devin" and token

    # token errado → PORTAL-PLAN-STALE
    code, env = _call(server, "POST", "/installation/apply", {
        "scope": "project", "host": "devin", "profile": "minimal",
        "plan": plan, "plan_token": "forjado", "confirm": "apply"})
    assert code == 409
    assert env["error"]["code"] == "PORTAL-PLAN-STALE"

    # sem confirm → PORTAL-CONFIRM
    code, env = _call(server, "POST", "/installation/apply", {
        "scope": "project", "host": "devin", "profile": "minimal",
        "plan": plan, "plan_token": token})
    assert code == 400
    assert env["error"]["code"] == "PORTAL-CONFIRM"

    # fluxo correto
    code, env = _call(server, "POST", "/installation/apply", {
        "scope": "project", "host": "devin", "profile": "minimal",
        "plan": plan, "plan_token": token, "confirm": "apply"})
    assert code == 200
    assert env["data"]["status"] == "completed"
    # instalação mínima do devin é config-only: o ledger do manifesto é a prova
    manifesto = json.loads(
        (projeto / ".sparkforge_aws" / "integrations.json").read_text(encoding="utf-8")
    )
    assert "devin" in (manifesto.get("hosts") or {})
    assert env["data"]["verification"]["status"] == "PASS"

    code, env = _call(server, "GET", "/bootstrap")
    assert env["data"]["health"]["state"] in ("INSTALLED", "ACTIVE", "VERIFIED")


def test_install_plan_scope_invalido(server):
    code, env = _call(server, "POST", "/installation/plan", {"scope": "system"})
    assert code == 400
    assert env["error"]["code"] == "PORTAL-BAD-FIELD"


# ---------------------------------------------------------------------------
# tasks — intent → plan → execute, recusa nomeada para ambíguo
# ---------------------------------------------------------------------------

def test_task_doctor_roundtrip(server):
    code, env = _call(server, "POST", "/tasks/plan", {"intent": "doctor da instalação"})
    assert code == 200
    assert env["data"]["plan"]["verb"] == "doctor"
    code, env = _call(server, "POST", "/tasks/execute", {
        "plan": env["data"]["plan"], "plan_token": env["data"]["plan_token"],
        "confirm": "execute"})
    assert code == 200
    task = env["data"]["task"]
    assert task["stage"] == "completed"
    assert task["receipt"]["schema"].startswith("forge/")


def test_task_mcp_vem_antes_de_verificar(server):
    code, env = _call(server, "POST", "/tasks/plan",
                      {"intent": "verificar o handshake mcp"})
    assert code == 200
    assert env["data"]["plan"]["verb"] == "mcp_verify"


def test_task_intencao_ambigua_recusa_nomeada(server):
    code, env = _call(server, "POST", "/tasks/plan", {"intent": "apaga tudo"})
    assert code == 400
    err = env["error"]
    assert err["code"] == "SFA-PORTAL-AMBIGUOUS"
    assert "safe_verbs" in (err.get("details") or {})


def test_task_execute_exige_confirm_e_token(server):
    code, env = _call(server, "POST", "/tasks/plan", {"intent": "status"})
    plan, token = env["data"]["plan"], env["data"]["plan_token"]
    code, env = _call(server, "POST", "/tasks/execute",
                      {"plan": plan, "plan_token": token})
    assert code == 400
    assert env["error"]["code"] == "PORTAL-CONFIRM"


def test_tasks_listadas_apos_execucao(server):
    _call(server, "POST", "/tasks/plan", {"intent": "status"})
    code, env = _call(server, "GET", "/tasks")
    assert code == 200


def test_portal_verb_parseia():
    from sparkforge_aws.adapters.cli import build_parser

    args = build_parser().parse_args(["portal", "--no-browser", "--port", "0"])
    assert args.command == "portal"
    assert args.no_browser is True


def test_assets_index_resolvido():
    # clone ou wheel: um dos candidatos tem o index.html da SPA
    assert pa._ASSETS_DIR is not None
    assert (pa._ASSETS_DIR / "index.html").is_file()


# ---------------------------------------------------------------------------
# docs
# ---------------------------------------------------------------------------

def test_docs_search_inventory(server):
    code, env = _call(server, "GET", "/docs/search?q=glue")
    assert code == 200
    assert len(env["data"]) > 0
    assert all("path" in h and "title" in h for h in env["data"])


def test_docs_search_vazio_sem_query(server):
    code, env = _call(server, "GET", "/docs/search")
    assert code == 200
    assert env["data"] == []
