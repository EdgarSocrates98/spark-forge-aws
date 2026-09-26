"""Integracao do SparkForge por usuario: `sparkforge integrate` e `sparkforge detach`.

Grava skills, agents e o registro do MCP nos diretorios de USUARIO de cada host
(Claude Code, Devin CLI, Codex CLI, Copilot CLI), a partir do conteudo que o wheel
embute, e nunca dentro do repositorio. Desenho: docs/sdd/INTEGRACAO_USUARIO/design.md.
"""
from __future__ import annotations

import contextlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sparkforge import __version__
from sparkforge.integrate import claude as _claude
from sparkforge.integrate import conflict as _conflict
from sparkforge.integrate import sources, writer
from sparkforge.integrate.hosts import HOSTS, Host, mcp_command, mcp_entry
from sparkforge.integrate.hosts import host as _host

INTEGRAVEIS = HOSTS


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
        cli = r.get("claude_cli") or {}
        if cli.get("status") == "refused":
            recusas.append({"host": r["host"], **{k: v for k, v in cli.items() if k != "status"}})
    return recusas


def _recusado(home: Path, dry_run: bool, recusa: writer.ManifestoRecusado) -> dict[str, Any]:
    """Manifesto que nao pode guiar a escrita: nenhum host e tocado."""
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(home).as_posix(),
        "hosts": [],
        "refused": [recusa.as_dict()],
    }


def _integrar_host(
    h: Host,
    plano: list[tuple[Path, bytes]],
    *,
    disco: writer.Disco,
    manifesto: dict[str, Any],
    python: str | None,
    runner: _claude.Runner | None,
    which: _claude.Which | None,
) -> dict[str, Any]:
    nome = h.name
    primeira = not (manifesto["hosts"].get("claude") or {}).get("registered")
    relatorio = writer.apply_files(
        nome, plano, disco=disco, manifesto=manifesto, version=__version__
    )
    relatorio["config"] = _configurar(h, disco=disco, manifesto=manifesto, python=python)
    if nome == "claude":
        cli = _claude.register(
            disco.home, primeira=primeira,
            mudou=bool(relatorio["written"] or relatorio["removed"]),
            dry_run=disco.dry_run, runner=runner, which=which,
        )
        relatorio["claude_cli"] = cli
        if cli["status"] == "ok":
            manifesto["hosts"]["claude"]["registered"] = True
    return relatorio


def integrate(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    windows: bool | None = None,
    appdata: Path | None = None,
    codex_home: Path | None = None,
    python: str | None = None,
    runner: _claude.Runner | None = None,
    which: _claude.Which | None = None,
    root: Path | None = None,
    repo: Path | None = None,
    on_conflict: str | None = None,
    interactive: bool = False,
    prompt: Callable[[str], str] | None = None,
    announce: Callable[[list[str]], None] | None = None,
) -> dict[str, Any]:
    """Grava a integracao de `alvo` (um host ou `all`) sob `home`.

    `appdata=None` e `home/AppData/Roaming` e `codex_home=None` e `home/.codex`;
    o CLI passa o `%APPDATA%` e o `CODEX_HOME` reais.
    Com `repo`, confere a copia vendorizada em dobro nele e aplica a escolha do
    operador (D9); e a unica escrita possivel dentro de um repositorio. `announce`
    recebe a lista de arquivos, um por um, antes da primeira remocao no repo."""
    disco = writer.Disco(home, appdata, codex_home=codex_home, dry_run=dry_run)
    raiz = sources.content_root() if root is None else Path(root)
    try:
        manifesto = writer.load_manifest(disco.home)
        writer.ligar_disco(disco, manifesto)
    except writer.ManifestoRecusado as recusa:
        return _recusado(disco.home, dry_run, recusa)
    # Todos os hosts sao planejados e renderizados ANTES da primeira escrita: um
    # render que estoura no terceiro host de `all` nao deixa os dois primeiros
    # gravados.
    planos: list[tuple[Host, list[tuple[Path, bytes]]]] = []
    for nome in _nomes(alvo):
        h = _host(
            nome, home=disco.home, windows=windows, appdata=disco.appdata,
            codex_home=disco.codex_home,
        )
        plano = writer.plan_files(h, raiz)
        if nome == "claude":
            plano += _claude.plugin_files(
                disco.home, version=__version__, python=python, content=list(plano)
            )
        planos.append((h, plano))
    relatorios: list[dict[str, Any]] = []
    try:
        for h, plano in planos:
            relatorios.append(_integrar_host(
                h, plano, disco=disco, manifesto=manifesto, python=python,
                runner=runner, which=which,
            ))
    except BaseException:
        # Falha de escrita no meio (permissao, disco): o que ja foi gravado entra no
        # manifesto, para o proximo detach saber que e nosso.
        if not dry_run:
            with contextlib.suppress(OSError):
                writer.sincronizar(disco, manifesto)
                writer.save_manifest(disco.home, manifesto)
        raise
    if not dry_run:
        writer.sincronizar(disco, manifesto)
        writer.save_manifest(disco.home, manifesto)
    resultado: dict[str, Any] = {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(disco.home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }
    if repo is not None:
        resultado["conflict"] = _conferir_copia(
            Path(repo), raiz, disco=disco, dry_run=dry_run, on_conflict=on_conflict,
            interactive=interactive, prompt=prompt, alvos=_nomes(alvo),
            integrados=writer.integrated_hosts(manifesto),
            recusado=bool(resultado["refused"]),
            announce=announce,
        )
    return resultado


def _conferir_copia(
    repo: Path,
    raiz: Path,
    *,
    disco: writer.Disco,
    dry_run: bool,
    on_conflict: str | None,
    interactive: bool,
    prompt: Callable[[str], str] | None,
    alvos: list[str],
    integrados: list[str],
    recusado: bool,
    announce: Callable[[list[str]], None] | None,
) -> dict[str, Any]:
    """A copia em dobro que os hosts `alvos` carregam, e a escolha do operador.

    Host alvo com recusa (CLI do Claude ausente, config recusada, arquivo do
    usuario) nao chegou a ter a integracao completa: o repositorio nao e tocado e
    sai `conflito_nao_resolvido_por_recusa`, sem perguntar."""
    raizes = {"home": disco.home, "appdata": disco.appdata, "codex_home": disco.codex_home}
    achado = _conflict.detect(repo, root=raiz, **raizes)
    colisoes = _conflict.relevant(achado["collisions"], alvos)
    recusas = list(achado["refused"])
    motivo: str | None
    if recusas:
        # Sem repositorio, o HOME, o repositorio fonte: nada e avaliado nem tocado.
        return {
            "collisions": [], "choice": "ignore", "dry_run": dry_run,
            "planned_removals": [], "removed": [], "still_duplicated": [], "kept": [],
            "choice_reason": None, "refused": recusas,
        }
    repo = achado["repo"]
    if recusado:
        escolha, motivo = "ignore", "conflito_nao_resolvido_por_recusa"
        recusas.append({
            "reason": "conflito_nao_resolvido_por_recusa",
            "detail": "o host alvo saiu com recusa; resolva-a e rode o integrate de novo",
        })
    else:
        removiveis = [c for c in colisoes if not _conflict.missing_hosts(c, integrados)]
        escolha, motivo = _conflict.choose(
            removiveis, on_conflict=on_conflict, interactive=interactive, prompt=prompt
        )
    resolucao = _conflict.resolve(
        repo, colisoes, escolha, dry_run=dry_run, integrados=integrados, announce=announce,
        **raizes,
    )
    return {
        "collisions": [
            {k: c[k] for k in ("name", "kind", "location", "identical")} for c in colisoes
        ],
        **resolucao,
        "choice_reason": motivo,
        "refused": recusas + resolucao["refused"],
    }


def detach(
    alvo: str,
    *,
    home: Path,
    dry_run: bool = False,
    appdata: Path | None = None,
    codex_home: Path | None = None,
    runner: _claude.Runner | None = None,
    which: _claude.Which | None = None,
) -> dict[str, Any]:
    """Remove o que o manifesto registrou para `alvo` (D7).

    So sai arquivo que ainda tem o sha256 gravado e que nenhum outro host usa;
    o editado depois fica, como recusa `editado_pelo_usuario`, e o `preexistente`
    fica sempre. Da config de usuario sai so a entrada que o integrate pos.
    `appdata` e `codex_home` sao os mesmos que o integrate recebeu. O `claude`
    registrado sai primeiro pelo CLI dele (`uninstall` e `marketplace remove`); com
    o CLI ausente ou falhando, nada dele sai do disco nem do manifesto, o host fica
    `cli_pendente` e o detach seguinte conclui.
    """
    disco = writer.Disco(home, appdata, codex_home=codex_home, dry_run=dry_run)
    try:
        manifesto = writer.load_manifest(disco.home)
        writer.ligar_disco(disco, manifesto)
    except writer.ManifestoRecusado as recusa:
        return _recusado(disco.home, dry_run, recusa)
    relatorios: list[dict[str, Any]] = []
    for nome in _nomes(alvo):
        entrada = manifesto["hosts"].get(nome)
        if entrada is None:
            relatorios.append({"host": nome, "status": "not_integrated", "refused": []})
            continue
        registros = list(entrada.get("config") or [])
        registrado = bool(entrada.get("registered"))
        cli: dict[str, Any] | None = None
        if nome == "claude" and registrado:
            # Primeiro o CLI: com ele ausente ou falhando, o plugin segue registrado
            # no Claude, e apagar o marketplace do disco o deixaria apontando para
            # o nada. O host fica pendente e o detach seguinte conclui.
            cli = _claude.unregister(dry_run=dry_run, runner=runner, which=which)
            if cli["status"] not in ("ok", "dry_run"):
                relatorios.append({
                    "host": nome, "status": "cli_pendente", "claude_cli": cli,
                    "removed": [], "refused": [],
                })
                continue
        relatorio = writer.remove_owned(
            disco, manifesto, nome, writer.host_files(manifesto, nome)
        )
        relatorio["host"] = nome
        revertidos = [writer.revert_config(registro, disco=disco) for registro in registros]
        relatorio["config"] = revertidos
        # Config cujo revert foi recusado (JSON invalido, bloco quebrado, entrada
        # editada) fica no manifesto: depois do conserto, o detach seguinte conclui.
        pendentes = [
            registro
            for registro, revertido in zip(registros, revertidos, strict=True)
            if revertido["status"] == "refused"
        ]
        relatorio["status"] = "config_pendente" if pendentes else "detached"
        if cli is not None:
            relatorio["claude_cli"] = cli
        if pendentes:
            manifesto["hosts"][nome] = {
                "package_version": entrada.get("package_version"),
                "config": pendentes,
                "status": writer.CONFIG_PENDENTE,
            }
        else:
            del manifesto["hosts"][nome]
        relatorios.append(relatorio)
    if not dry_run:
        writer.drop_manifest_if_empty(disco, manifesto)
    return {
        "dry_run": dry_run,
        "manifest": writer.manifest_path(disco.home).as_posix(),
        "hosts": relatorios,
        "refused": _recusas(relatorios),
    }


def status(
    *,
    home: Path,
    repo: Path | None = None,
    appdata: Path | None = None,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    """O que o `doctor` le: o manifesto e, por host, a copia em dobro no `repo`.

    So le. Manifesto ilegivel levanta `ManifestoRecusado`, e o doctor o mostra
    como checagem. Sem repositorio git, o HOME e o repositorio fonte nao tem copia
    em dobro a acusar (`detect` os recusa)."""
    manifesto = writer.load_manifest(Path(home))
    em_dobro: dict[str, list[dict[str, Any]]] = {nome: [] for nome in HOSTS}
    if repo is not None:
        achado = _conflict.detect(
            Path(repo), home=Path(home), appdata=appdata, codex_home=codex_home
        )
        integrados = writer.integrated_hosts(manifesto)
        for colisao in achado["collisions"]:
            # A copia so sai pelo `resolve` com TODOS os hosts que a leem integrados:
            # `missing_hosts` diz quais faltam.
            faltam = _conflict.missing_hosts(colisao, integrados)
            for nome in colisao["hosts"]:
                em_dobro[nome].append({
                    "path": f"{colisao['location']}/{colisao['name']}",
                    "missing_hosts": [h for h in faltam if h != nome],
                })
    return {"manifest": manifesto, "duplicated": em_dobro}


__all__ = ["INTEGRAVEIS", "detach", "integrate", "status"]
