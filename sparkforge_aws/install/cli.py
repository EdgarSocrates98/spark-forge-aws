"""`sparkforge-aws install|status|repair|update|uninstall` — leaf dispatch.

Segue o padrao de `distribution/cli.py`: `dispatch(args)` e chamado por
`adapters/cli.py` quando `args.command` e um verbo do ciclo de vida.
Saida JSON por verbo; recusas sao documentos estruturados, nunca traceback.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sparkforge_aws import _installkit as kit
from sparkforge_aws.install import lifecycle

_HOSTS = ("claude", "devin", "codex", "copilot", "all")
_SCOPES = ("project", "workspace", "user")
_PROFILES = ("minimal", "recommended", "full")
_GATEWAY = ("economy", "balanced", "deep")


def _p(args: argparse.Namespace, name: str, default: Any = None) -> Any:
    return getattr(args, name, default)


def _print(doc: dict[str, Any]) -> None:
    print(json.dumps(doc, indent=2, sort_keys=True))


def _install(args: argparse.Namespace) -> dict[str, Any]:
    return lifecycle.install(
        _p(args, "host", "all"),
        scope=_p(args, "scope", "project"),
        root=Path(_p(args, "root")) if _p(args, "root") else None,
        profile=_p(args, "profile", "recommended"),
        gateway_profile=_p(args, "gateway_profile"),
        dry_run=_p(args, "dry_run", False),
        yes=_p(args, "yes", False),
    )


def _status(args: argparse.Namespace) -> dict[str, Any]:
    return lifecycle.status(
        scope=_p(args, "scope", "project"),
        root=Path(_p(args, "root")) if _p(args, "root") else None)


def _doctor(args: argparse.Namespace) -> dict[str, Any]:
    return lifecycle.doctor(
        scope=_p(args, "scope", "project"),
        root=Path(_p(args, "root")) if _p(args, "root") else None)


def _repair(args: argparse.Namespace) -> dict[str, Any]:
    return lifecycle.repair(
        scope=_p(args, "scope", "project"),
        root=Path(_p(args, "root")) if _p(args, "root") else None,
        dry_run=_p(args, "dry_run", False))


def _update(args: argparse.Namespace) -> dict[str, Any]:
    return lifecycle.update(
        to=_p(args, "to"), repo=Path(_p(args, "repo")) if _p(args, "repo") else None,
        dry_run=_p(args, "dry_run", False))


def _uninstall(args: argparse.Namespace) -> dict[str, Any]:
    return lifecycle.uninstall(
        scope=_p(args, "scope", "project"), host=_p(args, "host", "all"),
        root=Path(_p(args, "root")) if _p(args, "root") else None,
        purge=_p(args, "purge", False), dry_run=_p(args, "dry_run", False))


def _mcp_verify(args: argparse.Namespace) -> dict[str, Any]:
    return lifecycle.mcp_verify()


def _wrap(fn) -> Any:
    def run(args: argparse.Namespace) -> dict[str, Any]:
        try:
            return fn(args)
        except kit.InstallError as exc:
            return exc.document("spark-forge-aws")
        except Exception as exc:  # boundary: structured refusal, not traceback
            return {"schema": kit.SCHEMA_RECEIPT, "forge_id": "spark-forge-aws",
                    "status": "failed", "checks": [],
                    "managed_files": [],
                    "verification": {"status": "FAIL"},
                    "error": {"kind": "SF-INSTALL-INTERNAL", "detail": str(exc)}}
    return run


_HANDLERS = {
    ("install", None): _install,
    ("status", None): _status,
    ("install", "doctor"): _doctor,
    ("doctor", "install"): _doctor,
    ("repair", None): _repair,
    ("update", None): _update,
    ("uninstall", None): _uninstall,
    ("mcp", "verify"): _mcp_verify,
}

_COMMANDS = {"install", "status", "repair", "update", "uninstall"}


def dispatch(args: argparse.Namespace) -> int:
    sub = (getattr(args, "install_action", None)
           or getattr(args, "mcp_action", None)
           or getattr(args, "doctor_action", None)
           or getattr(args, "subcommand", None))
    fn = _HANDLERS.get((args.command, sub)) or _HANDLERS.get((args.command, None))
    if fn is None:
        print(json.dumps({"error": {"kind": "SF-INSTALL-VERB",
                                    "detail": f"unknown: {args.command} {sub}"}}))
        return 2
    out = _wrap(fn)(args)
    _print(out)
    return 0 if out.get("status") in ("completed", "planned") else 1


def add_parsers(sub: argparse._SubParsersAction) -> None:
    """Registra os verbos no parser principal (chamado por adapters/cli.py)."""
    hosts, scopes = _HOSTS, _SCOPES

    install_p = sub.add_parser(
        "install",
        help=("Instala o SparkForge no projeto/workspace (--scope) ou no HOME "
              "(--scope user, delegado ao integrate). Escreve so arquivos "
              "gerenciados; --dry-run mostra o plano."))
    install_p.add_argument("--scope", choices=scopes, default="project")
    install_p.add_argument("--host", choices=hosts, default="all")
    install_p.add_argument("--profile", choices=_PROFILES, default="recommended")
    install_p.add_argument("--gateway-profile", choices=_GATEWAY, default=None,
                           dest="gateway_profile")
    install_p.add_argument("--root", default=None,
                           help="Raiz do alvo (default: raiz do VCS ou cwd).")
    install_p.add_argument("--yes", "-y", action="store_true",
                           help="Aprovacao explicita: sem ela, --dry-run.")
    install_p.add_argument("--dry-run", action="store_true")
    install_sub = install_p.add_subparsers(dest="install_action")
    install_sub.add_parser("doctor", help="Saude da instalacao no alvo.")

    status_p = sub.add_parser(
        "status",
        help="Estado da instalacao (ledger + drift + health doc).")
    status_p.add_argument("--scope", choices=scopes, default="project")
    status_p.add_argument("--root", default=None)

    repair_p = sub.add_parser(
        "repair", help="Regrava assets gerenciados que sumiram ou mudaram.")
    repair_p.add_argument("--scope", choices=scopes, default="project")
    repair_p.add_argument("--root", default=None)
    repair_p.add_argument("--dry-run", action="store_true")

    update_p = sub.add_parser(
        "update", help="Atualiza o runtime instalado pelo bootstrap.")
    update_p.add_argument("--to", default=None,
                          help="Versao pinned (nunca 'latest').")
    update_p.add_argument("--repo", default=None,
                          help="Checkout para instalar/atualizar.")
    update_p.add_argument("--dry-run", action="store_true")

    uninstall_p = sub.add_parser(
        "uninstall",
        help="Remove so o que o manifesto declara como gerenciado.")
    uninstall_p.add_argument("--scope", choices=scopes, default="project")
    uninstall_p.add_argument("--host", choices=hosts, default="all")
    uninstall_p.add_argument("--root", default=None)
    uninstall_p.add_argument("--purge", action="store_true",
                             help="Apaga tambem o state dir .sparkforge_aws/install.")
    uninstall_p.add_argument("--dry-run", action="store_true")

    mcp_p = sub.add_parser("mcp", help="Operacoes do servidor MCP.")
    mcp_sub = mcp_p.add_subparsers(dest="mcp_action")
    mcp_sub.add_parser(
        "verify",
        help="Handshake JSON-RPC real: initialize + tools/list contra o server.")


__all__ = ["add_parsers", "dispatch", "_COMMANDS"]
