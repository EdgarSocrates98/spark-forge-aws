"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import Host, mcp_entry
from sparkforge.integrate.hosts import host as _host

# Os hosts que esta versao integra. `claude` entra com o marketplace local (D8).
INTEGRAVEIS = ("devin", "codex", "copilot")


def _nomes(alvo: str) -> list[str]:
    if alvo == "all":
        return list(INTEGRAVEIS)
    if alvo not in INTEGRAVEIS:
        raise ValueError(f"host desconhecido: {alvo!r}; conhecidos: {[*INTEGRAVEIS, 'all']}")
    return [alvo]


def _configurar(
    h: Host, *, home: Path, manifesto: dict[str, Any], dry_run: bool, python: str | None
) -> list[dict[str, Any]]:
    """O servidor MCP na config de usuario do host, mesclado (D6)."""
    if h.mcp_config is None or h.mcp_format != "json":
        return []
    return [
        writer.apply_json_config(
            h.name, h.mcp_config, mcp_entry(h.name, python),
            home=home, manifesto=manifesto, dry_run=dry_run,
        )
    ]


def _recusas(relatorios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recusas = [{"host": r["host"], **recusa} for r in relatorios for recusa in r["refused"]]
    for r in relatorios:
        for config in r.get("config") or []:
            if config["status"] == "refused":
                recusas.append({"host": r["host"], "reason": config["reason"],
                                "path": config["path"]})
    return recusas


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    python: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`."""
    home = Path(home)
    raiz = sources.content_root() if root is None else Path(root)
    manifesto = writer.load_manifest(home)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=home, windows=windows, appdata=appdata)
        plano = writer.plan_files(h, raiz)
        relatorio = writer.apply_files(
            nome, plano, home=home, manifesto=manifesto, version=__version__,
            dry_run=dry_run,
        )
        relatorio["config"] = _configurar(
            h, home=home, manifesto=manifesto, dry_run=dry_run, python=python
        )
        relatorios.append(relatorio)
    if not dry_run:
        writer.save_manifest(home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


__all__ = ["INTEGRAVEIS", "integrate"]
