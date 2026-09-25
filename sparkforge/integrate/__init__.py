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
from sparkforge.integrate.hosts import Host, mcp_command, mcp_entry
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
    h: Host, *, disco: writer.Disco, manifesto: dict[str, Any], python: str | None
) -> list[dict[str, Any]]:
    """O servidor MCP na config de usuario do host, mesclado (D6)."""
    if h.mcp_config is None:
        return []
    if h.mcp_format == "toml":
        comando, args = mcp_command(python)
        return [
            writer.apply_toml_config(
                h.name, h.mcp_config, writer.toml_block(comando, args),
                disco=disco, manifesto=manifesto,
            )
        ]
    return [
        writer.apply_json_config(
            h.name, h.mcp_config, mcp_entry(h.name, python),
            disco=disco, manifesto=manifesto,
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


def _recusado(home: Path, dry_run: bool, recusa: writer.ManifestoRecusado) -> dict[str, Any]:
    """Manifesto que nao pode guiar a escrita: nenhum host e tocado."""
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": [],
        "refused": [recusa.as_dict()],
    }


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
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`.

    `appdata=None` e `home/AppData/Roaming`; o CLI passa o `%APPDATA%` real."""
    disco = writer.Disco(home, appdata, dry_run=dry_run)
    raiz = sources.content_root() if root is None else Path(root)
    try:
        manifesto = writer.load_manifest(disco.home)
    except writer.ManifestoRecusado as recusa:
        return _recusado(disco.home, dry_run, recusa)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        h = _host(nome, home=disco.home, windows=windows, appdata=disco.appdata)
        plano = writer.plan_files(h, raiz)
        relatorio = writer.apply_files(
            nome, plano, disco=disco, manifesto=manifesto, version=__version__
        )
        relatorio["config"] = _configurar(h, disco=disco, manifesto=manifesto, python=python)
        relatorios.append(relatorio)
    if not dry_run:
        writer.save_manifest(disco.home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(disco.home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


def detach(
    alvo: str, *, home: Path, dry_run: bool = False, appdata: Path | None = None
) -> dict[str, Any]:
    """Remove o que o manifesto registrou para `alvo` (D7).

    So sai arquivo que ainda tem o sha256 gravado e que nenhum outro host usa;
    o editado depois fica, como recusa `editado_pelo_usuario`, e o `preexistente`
    fica sempre. Da config de usuario sai so a entrada que o integrate pos.
    `appdata` e o mesmo que o integrate recebeu.
    """
    disco = writer.Disco(home, appdata, dry_run=dry_run)
    try:
        manifesto = writer.load_manifest(disco.home)
    except writer.ManifestoRecusado as recusa:
        return _recusado(disco.home, dry_run, recusa)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        entrada = manifesto["hosts"].get(nome)
        if entrada is None:
            relatorios.append({"host": nome, "status": "not_integrated", "refused": []})
            continue
        registros = list(entrada.get("config") or [])
        relatorio = writer.remove_owned(
            disco, manifesto, nome, writer.host_files(manifesto, nome)
        )
        relatorio["host"] = nome
        relatorio["status"] = "detached"
        relatorio["config"] = [
            writer.revert_config(registro, disco=disco) for registro in registros
        ]
        if not dry_run:
            del manifesto["hosts"][nome]
        relatorios.append(relatorio)
    if not dry_run:
        writer.drop_manifest_if_empty(disco.home, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(disco.home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


__all__ = ["INTEGRAVEIS", "detach", "integrate"]
