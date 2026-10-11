"""Portal adapter for SparkForge AWS — maps forge/PortalApi/1 operations
onto the real install/lifecycle, integrate/open_host, registry and
graphview services. Nothing here fabricates state: every field comes
from a real service call; unverifiable values stay `unverified`.
"""
from __future__ import annotations

import json
import sys
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from sparkforge_aws import _forge_portal as fp
from sparkforge_aws.install import lifecycle

_PACKAGE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_ROOT.parent
# Clone layout: portal/assets na raiz. Wheel layout: force-include copia para
# sparkforge_aws/portal_assets/ (mesmo padrão do integrate/bundle).
_ASSETS_CANDIDATES = (
    _PACKAGE_ROOT / "portal_assets",
    _REPO_ROOT / "portal" / "assets",
)
_ASSETS_DIR = next((d for d in _ASSETS_CANDIDATES if (d / "index.html").is_file()), None)
_INVENTORY = _REPO_ROOT / "docs" / "knowledge-program" / "inventory.jsonl"
# Catalog: clone lê o repo; wheel lê o bundle force-included (integrate/bundle).
_CATALOG_CANDIDATES = (
    _REPO_ROOT,
    _PACKAGE_ROOT / "integrate" / "bundle",
)
_HOSTS = ("claude", "devin", "codex", "copilot")
_PROFILES = ("minimal", "recommended", "full")
_SCOPES = ("project", "workspace", "user")


def _version() -> str:
    try:
        return importlib_metadata.version("sparkforge-aws")
    except importlib_metadata.PackageNotFoundError:
        return "0.0.0+local"


def _health_state(status: dict[str, Any], doctor: dict[str, Any] | None) -> str:
    """Map the real lifecycle vocabulary — healthy|degraded|unverified|broken —
    onto the contract InstallState."""
    st = str((doctor or status).get("status") or "unverified").lower()
    if st == "unverified":
        return "NOT_INSTALLED"
    if st in ("degraded", "broken"):
        return "DEGRADED"
    if st == "healthy":
        checks = {c.get("id"): c.get("status") for c in (doctor or {}).get("checks", [])}
        mcp = checks.get("mcp-handshake")
        if mcp == "PASS":
            return "VERIFIED"
        if mcp in ("UNVERIFIED", "NOT_APPLICABLE"):
            return "ACTIVE"
        return "INSTALLED"
    return "NOT_INSTALLED"


class SparkForgePortal(fp.PortalAdapter):
    forge_id = "spark-forge-aws"
    forge_name = "Spark Forge AWS"
    forge_version = _version()
    cli = "sparkforge-aws"
    theme = "spark-forge-aws"
    federated = False

    def __init__(self, workspace: Path | None = None) -> None:
        self.workspace = str((workspace or Path.cwd()).resolve())
        self._root = Path(self.workspace)
        self.assets_dir = _ASSETS_DIR
        self._tasks: list[dict[str, Any]] = []
        self._task_seq = 0
        self.ops = fp.default_operations(self) + [
            fp.Operation("GET", "/profiles", lambda ctx: self._profiles()),
            fp.Operation("GET", "/hosts", lambda ctx: self._hosts()),
            fp.Operation("GET", "/mcp/servers", lambda ctx: self._mcp_servers()),
            fp.Operation("GET", "/skills", lambda ctx: self._skills()),
            fp.Operation("GET", "/agents", lambda ctx: self._agents()),
            fp.Operation("GET", "/tasks", lambda ctx: list(self._tasks)),
            fp.Operation("GET", "/graphs", lambda ctx: self._graphs()),
            fp.Operation("GET", "/docs/search", lambda ctx: self._docs_search(ctx)),
            fp.Operation("POST", "/installation/plan", self._install_plan, mutating=True),
            fp.Operation(
                "POST", "/installation/apply", self._install_apply,
                mutating=True, confirm="apply", needs_plan_token=True,
            ),
            fp.Operation(
                "POST", "/installation/repair", self._install_repair,
                mutating=True, confirm="repair",
            ),
            fp.Operation(
                "POST", "/installation/uninstall", self._install_uninstall,
                mutating=True, confirm="uninstall",
            ),
            fp.Operation(
                "POST", "/profiles/apply", self._profiles_apply,
                mutating=True, confirm="apply",
            ),
            fp.Operation("POST", "/hosts/launch", self._hosts_launch, mutating=False),
            fp.Operation("POST", "/mcp/verify", self._mcp_verify, mutating=True, confirm="verify"),
            fp.Operation("POST", "/tasks/plan", self._tasks_plan, mutating=True),
            fp.Operation(
                "POST", "/tasks/execute", self._tasks_execute,
                mutating=True, confirm="execute", needs_plan_token=True, timeout=120,
            ),
        ]

    # ------------------------------------------------------------------
    # descriptor / health / capabilities
    # ------------------------------------------------------------------
    def capabilities(self) -> list[dict]:
        caps = [
            {"id": "install", "state": "supported"},
            {"id": "hosts", "state": "supported"},
            {"id": "mcp", "state": "supported"},
            {"id": "skills", "state": "supported"},
            {"id": "agents", "state": "supported"},
            {"id": "tasks", "state": "supported"},
            {"id": "docs", "state": "supported" if _INVENTORY.is_file() else "unverified"},
            {
                "id": "graph",
                "state": "supported" if self._graph_available() else "unverified",
            },
        ]
        return caps

    def nav(self) -> list[dict]:
        return [
            {
                "id": "tasks",
                "label_key": "nav.tasks",
                "route": "/tasks",
                "requires_capability": "tasks",
            },
            {
                "id": "graph",
                "label_key": "nav.graph",
                "route": "/graph",
                "requires_capability": "graph",
            },
        ]

    def _graph_available(self) -> bool:
        try:
            from sparkforge_aws import graphview

            return graphview.build_view(self._root) is not None
        except Exception:  # noqa: BLE001 — availability probe, honest fallback
            return False

    def health(self) -> dict:
        status = self._status_doc()
        doctor = None
        doctor_error: str | None = None
        try:
            doctor = lifecycle.doctor(scope="project", root=self._root)
        except Exception as e:  # noqa: BLE001 — doctor failure degrades, never crashes bootstrap
            doctor_error = f"{type(e).__name__}: {e}"
        checks = []
        for c in (doctor or {}).get("checks", []):
            checks.append({
                "id": c.get("id", "check"),
                "state": c.get("status", "UNVERIFIED"),
                "detail": c.get("detail"),
            })
        if doctor_error:
            checks.append({"id": "doctor", "state": "UNVERIFIED", "detail": doctor_error})
        return {
            "state": _health_state(status, doctor),
            "checks": checks,
            "workspace": self.workspace,
            "profile": status.get("profile") if status.get("profile") else None,
            "updated_at": status.get("checked_at"),
        }

    def installation_status(self, ctx: fp.RequestContext | None = None) -> dict:  # noqa: ARG002
        return self.health()

    def _status_doc(self) -> dict[str, Any]:
        try:
            return lifecycle.status(scope="project", root=self._root)
        except Exception:  # noqa: BLE001
            return {"ledger_entries": 0, "drift": {}, "status": "unverified"}

    # ------------------------------------------------------------------
    # installation lifecycle — plan → confirm → apply, real receipts
    # ------------------------------------------------------------------
    def _install_plan(self, ctx: fp.RequestContext) -> dict:
        scope = (ctx.body or {}).get("scope", "project")
        if scope not in _SCOPES:
            raise fp.PortalError(
                "PORTAL-BAD-FIELD", f"scope must be one of {_SCOPES}",
                details={"field": "scope", "got": scope},
            )
        host = (ctx.body or {}).get("host", "all")
        if host != "all" and host not in _HOSTS:
            raise fp.PortalError(
                "PORTAL-BAD-FIELD", f"host must be one of {_HOSTS + ('all',)}",
                details={"field": "host", "got": host},
            )
        profile = (ctx.body or {}).get("profile", "recommended")
        plan_input = {"scope": scope, "profile": profile, "host": host}
        receipt = lifecycle.install(
            host, scope=scope, root=self._root, profile=profile, dry_run=True,
        )
        return {
            "status": receipt.get("status", "planned"),
            "plan": plan_input,
            "plan_token": ctx.handler.server.sign_plan(plan_input),
            "receipt": receipt,
            "actions": [
                {
                    "kind": f.get("kind", "file"),
                    "path": f.get("path", ""),
                    "status": f.get("action", "planned"),
                }
                for f in receipt.get("managed_files", [])
            ],
        }

    def _install_apply(self, ctx: fp.RequestContext) -> dict:
        # The echoed plan is the source of truth — the token binds to it.
        plan = (ctx.body or {}).get("plan") or {}
        if not ctx.handler.server.check_plan(ctx.body["plan_token"], plan):
            raise fp.PortalError(
                "PORTAL-PLAN-STALE",
                "plan token does not match this plan or expired — regenerate the plan",
                http=409, retryable=True, action="regenerate_plan",
            )
        return lifecycle.install(
            plan.get("host", "all"),
            scope=plan.get("scope", "project"), root=self._root,
            profile=plan.get("profile", "recommended"),
            dry_run=False, yes=True,
        )

    def _install_repair(self, ctx: fp.RequestContext) -> dict:  # noqa: ARG002
        return lifecycle.repair(scope="project", root=self._root)

    def _install_uninstall(self, ctx: fp.RequestContext) -> dict:
        host = (ctx.body or {}).get("host", "all")
        return lifecycle.uninstall(scope="project", host=host, root=self._root)

    # ------------------------------------------------------------------
    # profiles
    # ------------------------------------------------------------------
    def _profiles(self) -> list[dict]:
        current = self._installed_profile()
        return [
            {
                "id": "economy",
                "label_key": "profiles.economy",
                "description_key": "profiles.economy.desc",
                "current": current == "economy",
                "components": {
                    "skills": False, "agents": False, "mcp": True,
                    "tui": False, "graph_studio": False,
                },
            },
            {
                "id": "balanced",
                "label_key": "profiles.balanced",
                "description_key": "profiles.balanced.desc",
                "current": current == "balanced",
                "components": {
                    "skills": True, "agents": True, "mcp": True,
                    "tui": True, "graph_studio": False,
                },
            },
            {
                "id": "full",
                "label_key": "profiles.full",
                "description_key": "profiles.full.desc",
                "current": current == "full",
                "components": {
                    "skills": True, "agents": True, "mcp": True,
                    "tui": True, "graph_studio": True,
                },
            },
        ]

    def _installed_profile(self) -> str:
        """Profile of the newest install receipt — honest None when uninstalled."""
        receipts = sorted((self._root / ".sparkforge_aws" / "receipts").glob("install-*.json"))
        for path in reversed(receipts):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if doc.get("operation") == "install" and doc.get("status") == "completed":
                return {
                    "minimal": "economy", "recommended": "balanced", "full": "full",
                }.get(str(doc.get("profile") or "").lower(), "")
        return ""

    def _profiles_apply(self, ctx: fp.RequestContext) -> dict:
        profile = (ctx.body or {}).get("profile", "balanced")
        real = {"economy": "minimal", "balanced": "recommended", "full": "full"}.get(profile)
        if real is None:
            raise fp.PortalError(
                "PORTAL-BAD-FIELD", f"profile must be one of {_PROFILES + ('economy','balanced')}",
                details={"field": "profile", "got": profile},
            )
        return lifecycle.install(
            "all", scope="project", root=self._root, profile=real,
            dry_run=False, yes=True,
        )

    # ------------------------------------------------------------------
    # hosts — observe-only; launch returns the command to copy
    # ------------------------------------------------------------------
    def _hosts(self) -> list[dict]:
        from sparkforge_aws.integrate import open_host

        out: list[dict] = []
        for host in _HOSTS:
            try:
                flow = open_host.ai_flow(host, repo=self._root, launch=False)
            except Exception as e:  # noqa: BLE001 — per-host probe degrades honestly
                out.append({
                    "host": host, "detected": False, "version": None,
                    "supported": False, "logged_in": None,
                    "integration": "unverified", "launchable": False,
                    "detail": f"probe failed: {type(e).__name__}",
                })
                continue
            for h in flow.get("hosts", []):
                integration = h.get("integration") or {}
                # state: NOT_DETECTED|DETECTED|SUPPORTED|READY|NEEDS_LOGIN|
                # INTEGRATION_DEGRADED|INTEGRATION_BROKEN (open_host.ai_flow)
                detected = h.get("binary_path") is not None
                out.append({
                    "host": h.get("host", host),
                    "detected": detected,
                    "version": h.get("version"),
                    "supported": h.get("state") in ("READY", "SUPPORTED"),
                    "logged_in": h.get("logged_in"),
                    "integration": integration.get("state", "unverified"),
                    "launchable": detected,
                    "command_hint": h.get("launch_command") if detected else None,
                    "detail": h.get("detail") or h.get("login_hint"),
                })
        return out

    def _hosts_launch(self, ctx: fp.RequestContext) -> dict:
        host = (ctx.body or {}).get("host")
        if host not in _HOSTS:
            raise fp.PortalError(
                "PORTAL-BAD-FIELD", f"host must be one of {_HOSTS}",
                details={"field": "host", "got": host},
            )
        from sparkforge_aws.integrate import open_host

        flow = open_host.ai_flow(host, repo=self._root, launch=False)
        for h in flow.get("hosts", []):
            # NOT_DETECTED hosts still carry a launch_command string — the
            # binary is the evidence, not the label.
            if h.get("binary_path") is None:
                return {
                    "command": None,
                    "refusal": "PORTAL-HOST-ABSENT",
                    "detail": f"{host} not detected on this system",
                }
            # A portal has no real TTY — return the command to copy.
            return {
                "command": h.get("launch_command"),
                "detail": f"run `{h.get('launch_command')}` in your terminal to open {host}",
                "host": h.get("host"),
            }
        return {"command": None, "refusal": "PORTAL-HOST-ABSENT", "detail": f"{host} not detected"}

    # ------------------------------------------------------------------
    # mcp
    # ------------------------------------------------------------------
    def _mcp_verify_doc(self) -> dict[str, Any]:
        try:
            return lifecycle.mcp_verify()
        except Exception as e:  # noqa: BLE001
            return {
                "status": "FAIL",
                "detail": f"mcp verify failed: {type(e).__name__}",
                "tools": [],
            }

    def _mcp_servers(self) -> list[dict]:
        doc = self._mcp_verify_doc()
        status = doc.get("status", "FAIL")
        tools = doc.get("tools") or []
        state = {
            "PASS": "INVOCATION_VERIFIED",
            "HANDSHAKE": "HANDSHAKE_VERIFIED",
            "FAIL": "FAILED",
        }.get(status, "DEGRADED")
        return [{
            "id": "sparkforge-aws",
            "state": state,
            "host": None,
            "tools_count": len(tools) or None,
            "last_verify": doc.get("checked_at"),
            "detail": doc.get("detail"),
        }]

    def _mcp_verify(self, ctx: fp.RequestContext) -> dict:  # noqa: ARG002
        doc = self._mcp_verify_doc()
        return {
            "status": doc.get("status", "FAIL"),
            "detail": doc.get("detail"),
            "actions": [
                {
                    "kind": "handshake",
                    "path": "mcp://sparkforge-aws",
                    "status": doc.get("status", "FAIL"),
                }
            ],
        }

    # ------------------------------------------------------------------
    # skills / agents — canonical registry
    # ------------------------------------------------------------------
    def _registry(self):
        from sparkforge_aws.registry.loader import CanonicalRegistry

        # Catalog = what this forge ships, never the user's workspace: the
        # clone registry root first, then the wheel's force-included bundle.
        failures: list[str] = []
        for root in _CATALOG_CANDIDATES:
            reg = CanonicalRegistry(root)
            try:
                reg.load_from_configs()
            except Exception as exc:  # noqa: BLE001 — try the next candidate
                failures.append(f"{root}: {type(exc).__name__}")
                continue
            if reg.skills or reg.agents:
                return reg
        raise fp.PortalError(
            "PORTAL-REGISTRY-UNAVAILABLE",
            "skill/agent catalog not found in clone or installed bundle",
            http=503, retryable=True,
            details={"candidates": [str(r) for r in _CATALOG_CANDIDATES], "failures": failures},
        )

    def _skills(self) -> list[dict]:
        reg = self._registry()
        out = []
        for sid, s in sorted(reg.skills.items()):
            out.append({
                "id": sid,
                "name": getattr(s, "name", sid),
                "domain": (getattr(s, "domains", None) or [None])[0]
                if isinstance(getattr(s, "domains", None), list)
                else getattr(s, "domain", None),
                "description": getattr(s, "description", "") or "",
                "state": "available",
                "hosts": [],
                "source": "registry",
            })
        return out

    def _agents(self) -> list[dict]:
        reg = self._registry()
        out = []
        for aid, a in sorted(reg.agents.items()):
            skills = getattr(a, "required_skills", []) or []
            optional = getattr(a, "optional_skills", []) or []
            out.append({
                "id": aid,
                "name": getattr(a, "name", aid),
                "role": getattr(a, "role", "") or "agent",
                "description": getattr(a, "description", "") or getattr(a, "purpose", "") or "",
                "authority": None,
                "domains": list(getattr(a, "domains", []) or []),
                "skills": list(skills) + list(optional),
                "hosts": [],
                "state": "available",
            })
        return out

    # ------------------------------------------------------------------
    # tasks — safe read-only diagnostics mapped from intent, real receipts
    # ------------------------------------------------------------------
    # Order matters — first needle hit wins. `mcp`/`handshake` precede the
    # generic `verif` needles so "verificar o handshake mcp" picks mcp_verify,
    # and `doctor` precedes `instala` so "doctor da instalação" is not status.
    _SAFE_TASKS: tuple[tuple[tuple[str, ...], str, str], ...] = (
        (("mcp", "handshake"), "mcp_verify", "MCP handshake verification"),
        (("doctor", "saúde", "saude", "verifica", "verif"), "doctor", "installation doctor"),
        (("status", "estado", "instala"), "status", "installation status"),
        (("grafo", "graph"), "graph", "graph summary"),
        (("skill",), "skills", "skill catalog summary"),
        (("agent",), "agents", "agent roster summary"),
    )

    def _intent_to_task(self, intent: str) -> tuple[str, str] | None:
        low = intent.lower()
        for needles, verb, label in self._SAFE_TASKS:
            if any(n in low for n in needles):
                return verb, label
        return None

    def _tasks_plan(self, ctx: fp.RequestContext) -> dict:
        intent = ((ctx.body or {}).get("intent") or "").strip()
        if not intent:
            raise fp.PortalError(
                "PORTAL-MISSING-FIELD", "field 'intent' is required",
                details={"field": "intent"},
            )
        mapped = self._intent_to_task(intent)
        if mapped is None:
            verbs = sorted({v for _n, v, _l in self._SAFE_TASKS})
            raise fp.PortalError(
                "SFA-PORTAL-AMBIGUOUS",
                "intent does not map to a safe portal task",
                severity="warning",
                action="use one of the safe tasks",
                details={"safe_verbs": verbs, "intent": intent},
            )
        verb, label = mapped
        plan = {"verb": verb, "label": label, "intent": intent}
        return {
            "plan": plan,
            "plan_token": ctx.handler.server.sign_plan(plan),
            "status": "planned",
        }

    def _tasks_execute(self, ctx: fp.RequestContext) -> dict:
        plan = (ctx.body or {}).get("plan") or {}
        verb = plan.get("verb", "")
        if not ctx.handler.server.check_plan(ctx.body["plan_token"], plan):
            raise fp.PortalError(
                "PORTAL-PLAN-STALE",
                "plan token does not match — regenerate the plan",
                http=409, retryable=True, action="regenerate_plan",
            )
        self._task_seq += 1
        task_id = f"task-{self._task_seq}"
        record: dict[str, Any] = {
            "id": task_id, "verb": verb, "label": plan.get("label", verb),
            "stage": "running", "started_at": _now(), "finished_at": None,
            "exit_code": None,
        }
        try:
            result = self._run_safe_task(verb)
            record["stage"] = "completed"
            record["exit_code"] = 0
            record["receipt"] = result
        except fp.PortalError as e:
            record["stage"] = "refused"
            record["exit_code"] = 2
            record["refusal"] = e.code
            record["receipt"] = {"detail": str(e)}
        except Exception as e:  # noqa: BLE001 — task failure is data, not a crash
            record["stage"] = "failed"
            record["exit_code"] = 1
            record["receipt"] = {"error": f"{type(e).__name__}: {e}"}
        record["finished_at"] = _now()
        self._tasks.append(record)
        return {
            "status": record["stage"],
            "task": record,
            "actions": [{"kind": "task", "path": verb, "status": record["stage"]}],
        }

    def _run_safe_task(self, verb: str) -> dict[str, Any]:
        if verb == "status":
            return self._status_doc()
        if verb == "doctor":
            return lifecycle.doctor(scope="project", root=self._root)
        if verb == "mcp_verify":
            return self._mcp_verify_doc()
        if verb == "graph":
            view = self._graph_view()
            if view is None:
                raise fp.PortalError(
                    "SFA-PORTAL-NO-GRAPH", "no graph built in this workspace",
                    action="build the graph first",
                )
            return view
        if verb == "skills":
            return {"skills": len(self._skills())}
        if verb == "agents":
            return {"agents": len(self._agents())}
        raise fp.PortalError("PORTAL-UNSAFE-TASK", f"task '{verb}' is not in the safe set")

    # ------------------------------------------------------------------
    # graph
    # ------------------------------------------------------------------
    def _graph_view(self) -> dict[str, Any] | None:
        try:
            from sparkforge_aws import graphview

            view = graphview.build_view(self._root)
            if view is None:
                return None
            if hasattr(view, "to_dict"):
                return view.to_dict()
            if isinstance(view, dict):
                return view
            return json.loads(json.dumps(view, default=str))
        except Exception:  # noqa: BLE001
            return None

    def _graphs(self) -> dict:
        view = self._graph_view()
        if view is None:
            return {
                "availability": {
                    "state": "no_graph",
                    "detail": "no graph built in this workspace",
                    "unlock": "sparkforge-aws graph build --root .",
                },
                "views": [],
                "studio_url": None,
            }
        return {
            "availability": {"state": "available"},
            "views": [view],
            "studio_url": None,
        }

    # ------------------------------------------------------------------
    # docs search — inventory.jsonl title/excerpt, offline
    # ------------------------------------------------------------------
    def _docs_search(self, ctx: fp.RequestContext) -> list[dict]:
        query = (ctx.query.get("q") or [""])[0].strip().lower()
        limit = int((ctx.query.get("limit") or ["20"])[0])
        if not query or not _INVENTORY.is_file():
            return []
        hits: list[dict] = []
        terms = query.split()
        for line in _INVENTORY.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") not in (None, "active"):
                continue
            hay = " ".join(str(row.get(k) or "") for k in ("title", "path", "category")).lower()
            if not all(t in hay for t in terms):
                continue
            hits.append({
                "path": row.get("path", ""),
                "title": row.get("title") or Path(row.get("path", "")).stem,
                "excerpt": "",
                "category": row.get("category") or "doc",
            })
            if len(hits) >= limit:
                break
        return hits


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_server(workspace: Path | None = None, *, quiet: bool = True) -> fp.PortalServer:
    return fp.PortalServer(SparkForgePortal(workspace), quiet=quiet)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import webbrowser

    ap = argparse.ArgumentParser(
        prog="sparkforge-aws portal",
        description="Serve the Spark Forge AWS portal locally (127.0.0.1).",
    )
    ap.add_argument(
        "--no-browser", action="store_true",
        help="print the URL without opening the browser",
    )
    ap.add_argument("--port", type=int, default=0, help="port (0 = free port)")
    ap.add_argument("--root", default=None, help="workspace root (default: cwd)")
    args = ap.parse_args(argv)

    adapter = SparkForgePortal(Path(args.root) if args.root else Path.cwd())
    if adapter.assets_dir is None:
        print(
            json.dumps({
                "refusal": "SFA-PORTAL-NO-ASSETS",
                "detail": (
                    "portal assets not vendored — run `sparkforge-aws portal` "
                    "after `python scripts/vendor.py` in forge-portal"
                ),
            })
        )
        return 1
    server = fp.PortalServer(adapter, port=args.port, quiet=True)
    url = server.url
    print(
        json.dumps({
            "url": url,
            "note": "portal is optional — CLI/TUI/MCP keep working without it",
        })
    )
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
