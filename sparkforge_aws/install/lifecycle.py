"""Ciclo de vida `install/status/doctor/repair/uninstall` nos escopos
`project` e `workspace` — e a ponte para o `integrate`/`detach` no `user`.

Escreve com a mesma maquina de posse do `integrate` (`writer.Disco` +
manifesto em `.sparkforge_aws/integrations.json`): o que o integrate adota
como `preexistente` aqui tambem fica — uninstall so tira o que e nosso.

Documentos `forge/*` do contrato (receipts, health, workspace) vivem em
`.sparkforge_aws/install/`; o manifesto de integracao, em
`.sparkforge_aws/integrations.json` — os dois coexistem no state dir.
"""

from __future__ import annotations

import json
import sys
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge_aws import __version__
from sparkforge_aws import _forgecontext as fctx
from sparkforge_aws import _installkit as kit
from sparkforge_aws.install.hosts import HOSTS, project_host, project_plan
from sparkforge_aws.integrate import sources, writer
from sparkforge_aws.integrate.hosts import mcp_entry

STATE_DIR = ".sparkforge_aws"
RECEIPTS_DIR = "receipts"

FORGE_ID = "spark-forge-aws"
PACKAGE = "sparkforge_aws"
DIST = "sparkforge-aws"
CLI = "sparkforge-aws"
PYTHON_SPEC = ">=3.10"

PROFILES = ("minimal", "recommended", "full")
GATEWAY_PROFILES = ("economy", "balanced", "deep")


def _spec() -> kit.ForgeSpec:
    return kit.ForgeSpec(
        forge_id=FORGE_ID,
        package=PACKAGE,
        distribution=DIST,
        cli_name=CLI,
        python_spec=PYTHON_SPEC,
        state_dir=STATE_DIR,
        mcp_command=(sys.executable, "-m", "sparkforge_aws.adapters.mcp", "--transport", "stdio"),
        mcp_server_name="sparkforge-aws",
        mcp_verify_tool="sparkforge_aws_runtime_detect",
    )


def _content_root() -> Path:
    return sources.content_root()


def _profile_kinds(profile: str) -> tuple[bool, bool]:
    """(skills?, agents?) — component profile, independent from gateway."""
    return {
        "minimal": (False, False),
        "recommended": (True, True),
        "full": (True, True),
    }[profile]


# --------------------------------------------------------------------------
# install
# --------------------------------------------------------------------------


@dataclass
class InstallArgs:
    scope: str = "project"
    host: str = "all"
    profile: str = "recommended"
    gateway_profile: str | None = None
    root: Path | None = None
    dry_run: bool = False
    yes: bool = False


def _hosts_for(alvo: str) -> list[str]:
    """``all`` → todos; ``none``/vazio → opt-out explícito (nunca todos);
    nome único ou csv → subconjunto validado (GAP-003)."""
    if alvo == "all":
        return list(HOSTS)
    if not alvo or alvo == "none":
        return []
    nomes = [h.strip() for h in alvo.split(",") if h.strip()]
    desconhecidos = [h for h in nomes if h not in HOSTS]
    if desconhecidos:
        raise kit.InstallError(
            kit.E_HOST,
            f"host {desconhecidos[0]!r}; conhecidos: {list(HOSTS)} + all,none",
        )
    return list(dict.fromkeys(nomes))


# Marcadores legados de geracoes anteriores do install — `install_docs` os
# remove ao convergir AGENTS.md/CLAUDE.md para o contrato `forge:<tag>`.
_LEGACY_DOC_TAGS: tuple[str, ...] = ("sparkforge-aws:managed",)

# Documentos de consumer gerenciados pela camada forge_context (nao pela
# ledger de arquivos — conteudo fora dos marcadores `forge:*` e do usuario).
_CONSUMER_DOCS: tuple[str, ...] = ("AGENTS.md", "CLAUDE.md", "AGENT_PROTOCOL.md")


def install(
    alvo: str = "all",
    *,
    host: str | None = None,
    scope: str = "project",
    root: Path | None = None,
    profile: str = "recommended",
    gateway_profile: str | None = None,
    python: str | None = None,
    dry_run: bool = False,
    yes: bool = False,
    cwd: Path | None = None,
    components: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Instala o Forge no projeto/workspace (ou no HOME via `integrate`)."""
    # Shared wizard contract calls every forge with ``host=``. Keep legacy
    # positional ``alvo`` compatible for CLI/portal callers while accepting
    # canonical keyword spelling.
    if host is not None:
        alvo = host
    if profile not in PROFILES:
        raise kit.InstallError(kit.E_PROFILE, f"profile {profile!r}; {PROFILES}")
    if scope == "user":
        return _install_user(alvo, profile, gateway_profile, python, dry_run, yes)

    cwd = Path(cwd or Path.cwd())
    spec = _spec()
    target = kit.resolve_scope(spec, scope, cwd, root)
    state = kit.state_dir_for(spec, scope, target)
    content = _content_root()
    opts = kit.component_options(profile, components)
    if components is None:
        skills, agents = _profile_kinds(profile)
        mcp_enabled = True
    else:
        selected_kinds = set(opts.get("asset_kinds", ()))
        skills = "skill" in selected_kinds
        agents = "agent" in selected_kinds
        mcp_enabled = "mcp" in selected_kinds

    nomes = _hosts_for(alvo)
    disco = writer.Disco(target, dry_run=dry_run)
    manifesto = writer.load_manifest(target)

    if not yes and not dry_run:
        raise kit.InstallError(
            kit.E_NOTAPPROVED, "install escreve no projeto; use --yes ou --dry-run"
        )

    lock = kit.acquire_lock(state) if not dry_run else nullcontext()
    with lock:
        plano_total: list[dict[str, Any]] = []
        relatorios: list[dict[str, Any]] = []
        # `.mcp.json` e UM arquivo compartilhado no projeto: todo host aponta
        # para ele. Escreve uma unica vez por install — senao o 2o+ host
        # dedupa como `ja_configurado` e a recusa vira FAIL no recibo de uma
        # instalacao correta. A entrada e sempre a forma simples
        # (command/args): valida para os quatro hosts; os campos extras do
        # copilot ficam para o mcp-config.json de usuario dele.
        mcp_escritos: set[str] = set()
        for nome in nomes:
            h = project_host(nome, target)
            plano = project_plan(h, content, target)
            filtrado = [(d, b) for d, b in plano if _want_file(d, target, skills, agents)]
            plano_total += [{"path": disco.chave(d), "bytes": len(b)} for d, b in filtrado]
            rel = writer.apply_files(
                nome, filtrado, disco=disco, manifesto=manifesto, version=__version__
            )
            configs = []
            if h.mcp_config is not None:
                chave_mcp = disco.chave(h.mcp_config)
                if mcp_enabled and chave_mcp not in mcp_escritos:
                    mcp_escritos.add(chave_mcp)
                    dono = next((n for n in nomes if n != "copilot"), nome)
                    configs.append(
                        writer.apply_json_config(
                            nome,
                            h.mcp_config,
                            mcp_entry(dono, python or sys.executable, profile=gateway_profile),
                            disco=disco,
                            manifesto=manifesto,
                        )
                    )
            rel["config"] = configs
            relatorios.append(rel)

        # AGENTS.md/CLAUDE.md/AGENT_PROTOCOL.md sao gerenciados pela camada
        # forge_context (blocos `forge:<forge-id>` + protocolo consolidado) —
        # gravados em `_register_context`, fora do disco/ledger de assets.
        # Entradas `marker` de installs antigos sao removidas da ledger: o
        # arquivo agora tem dono na camada de docs, nao hash de arquivo
        # inteiro (conteudo do usuario fora dos marcadores nao e drift).
        for doc_name in _CONSUMER_DOCS:
            manifesto["files"].pop(disco.chave(target / doc_name), None)

        escritos = sum(len(r.get("written") or []) for r in relatorios)
        removidos = sum(len(r.get("removed") or []) for r in relatorios)
        notas: list[dict[str, Any]] = []
        if "codex" in nomes:
            # Observado no Codex 0.160.0: `mcp list` ignora `.mcp.json` de
            # projeto e `.codex/config.toml` de projeto — MCP so entra por
            # `~/.codex/config.toml` (escopo user) ou `codex mcp add`.
            notas.append(
                {
                    "id": "mcp-scope:codex",
                    "status": "NOT_APPLICABLE",
                    "detail": "codex nao le .mcp.json de projeto; MCP exige "
                    "--scope user ou `codex mcp add`",
                }
            )
        recusas = [
            {"host": r["host"], **rec} for r in relatorios for rec in (r.get("refused") or [])
        ]
        for r in relatorios:
            for c in r.get("config") or []:
                if c["status"] == "refused":
                    recusas.append({"host": r["host"], "reason": c["reason"], "path": c["path"]})
        if not dry_run:
            writer.save_manifest(target, manifesto)

    receipt = _receipt(
        "install",
        scope,
        target,
        profile,
        managed=[
            {
                "path": f["path"],
                "sha256": "",
                "kind": "skill" if "skills" in f["path"] else "agent",
                "action": "written",
            }
            for f in plano_total
        ],
        markers=[
            {"file": d, "marker": f"forge:{FORGE_ID}"} for d in _CONSUMER_DOCS
        ],
        checks=[
            {"id": "files", "status": "PASS", "detail": f"{escritos} written, {removidos} removed"},
            {
                "id": "refusals",
                "status": "PASS" if not recusas else "FAIL",
                "detail": f"{len(recusas)} refused",
            },
        ]
        + notas,
        refused=recusas,
        dry_run=dry_run,
        status="planned" if dry_run else ("completed" if not recusas else "failed"),
    )
    if opts:
        receipt["components"] = opts
    if not dry_run:
        if opts:
            state.mkdir(parents=True, exist_ok=True)
            (state / "components.json").write_text(json.dumps(opts, indent=2), encoding="utf-8")
        _register_context(
            target,
            receipt,
            scope=scope,
            profile=profile,
            hosts=nomes,
            components=opts or None,
        )
        _write_receipt(state, receipt)
        _write_workspace_doc(scope, target, receipt)
        _register(target)
    return receipt


def _want_file(destino: Path, target: Path, skills: bool, agents: bool) -> bool:
    try:
        rel = destino.resolve().relative_to(target.resolve()).as_posix()
    except ValueError:
        return True
    is_skill = "/skills/" in f"/{rel}" or destino.name == "SKILL.md"
    return skills if is_skill else agents


def _install_user(
    alvo: str,
    profile: str,
    gateway_profile: str | None,
    python: str | None,
    dry_run: bool,
    yes: bool,
) -> dict[str, Any]:
    """Escopo `user` = `integrate` existente (HOME)."""
    from sparkforge_aws.integrate import integrate as _integrate

    if not yes and not dry_run:
        raise kit.InstallError(
            kit.E_NOTAPPROVED, "install --scope user escreve no HOME; use --yes ou --dry-run"
        )
    out = _integrate(
        alvo,
        home=Path.home(),
        dry_run=dry_run,
        profile=gateway_profile if gateway_profile in GATEWAY_PROFILES else None,
        python=python,
    )
    out["profile"] = profile
    out["scope"] = "user"
    return out


# --------------------------------------------------------------------------
# status / doctor / repair / uninstall
# --------------------------------------------------------------------------


def status(
    *, scope: str = "project", root: Path | None = None, cwd: Path | None = None
) -> dict[str, Any]:
    spec = _spec()
    cwd = Path(cwd or Path.cwd())
    if scope == "user":
        from sparkforge_aws.integrate import status as _status

        return _status(home=Path.home())
    target = kit.resolve_scope(spec, scope, cwd, root)
    manifesto = writer.load_manifest(target)
    files = manifesto.get("files") or {}
    drift = []
    disco = writer.Disco(target)
    for rel, reg in sorted(files.items()):
        dados = disco.ler(disco.local(rel))
        if dados is None:
            drift.append({"path": rel, "status": "missing"})
        elif writer.sha256_bytes(dados) != reg.get("sha256"):
            drift.append({"path": rel, "status": "modified"})
        else:
            drift.append({"path": rel, "status": "ok"})
    # Configs gerenciados (.mcp.json) vivem em hosts[*].config, fora do ledger
    # de arquivos: sem este bloco, um .mcp.json apagado reportava "healthy"
    # com o MCP quebrado. O que gerenciamos e a nossa entrada — outras chaves
    # do usuario nao sao nossa conta.
    vistos_cfg: set[str] = set()
    for nome in sorted(manifesto.get("hosts") or {}):
        for reg in manifesto["hosts"][nome].get("config") or []:
            rel = reg["path"]
            if rel in vistos_cfg:
                continue
            vistos_cfg.add(rel)
            dados = disco.ler(disco.local(rel))
            if dados is None:
                drift.append({"path": rel, "status": "missing", "kind": "config"})
                continue
            doc = None
            if reg.get("format") == "json":
                try:
                    doc = json.loads(dados.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    doc = None
            if isinstance(doc, dict):
                servidores = doc.get("mcpServers") or {}
                atual = next(
                    (servidores[k] for k in writer._SERVIDOR_KEYS if k in servidores), None
                )
                if atual is not None and writer._sha_entrada(atual) == reg.get("entry_sha256"):
                    drift.append({"path": rel, "status": "ok", "kind": "config"})
                else:
                    drift.append({"path": rel, "status": "modified", "kind": "config"})
            else:
                drift.append(
                    {
                        "path": rel,
                        "kind": "config",
                        "status": (
                            "ok"
                            if writer.sha256_bytes(dados) == reg.get("written_sha256")
                            else "modified"
                        ),
                    }
                )
    ok = sum(1 for d in drift if d["status"] == "ok")
    bad = [d for d in drift if d["status"] != "ok"]
    return {
        "schema": kit.SCHEMA_HEALTH,
        "forge_id": FORGE_ID,
        "scope": scope,
        "target_root": str(target),
        "state_dir": str(target / STATE_DIR),
        "ledger_entries": len(files),
        "drift": {
            "ok": ok,
            "modified": [d for d in bad if d["status"] == "modified"],
            "missing": [d for d in bad if d["status"] == "missing"],
        },
        "hosts": {n: sorted(writer.host_files(manifesto, n)) for n in manifesto.get("hosts", {})},
        "status": (
            "healthy"
            if files and not bad
            else "degraded"
            if ok
            else "unverified"
            if not files
            else "broken"
        ),
        "checked_at": kit._utc_now(),
    }


def doctor(
    *, scope: str = "project", root: Path | None = None, cwd: Path | None = None
) -> dict[str, Any]:
    st = status(scope=scope, root=root, cwd=cwd)
    checks: list[dict[str, Any]] = [
        {
            "id": "install-state",
            "status": st["status"].upper(),
            "detail": f"{st['ledger_entries']} ledger entries",
        }
    ]
    checks += [
        {"id": f"drift:{d['path']}", "status": "FAIL", "detail": d["status"], "repairable": True}
        for d in st["drift"]["modified"] + st["drift"]["missing"]
    ]
    import importlib.util

    if importlib.util.find_spec("mcp") is None:
        checks.append(
            {
                "id": "mcp-handshake",
                "status": "UNVERIFIED",
                "detail": "extra 'mcp' nao instalada — handshake nao testado",
            }
        )
    else:
        checks.append(
            kit.mcp_verify(
                kit.ForgeSpec(
                    forge_id=FORGE_ID,
                    package=PACKAGE,
                    distribution=DIST,
                    cli_name=CLI,
                    python_spec=PYTHON_SPEC,
                    state_dir=STATE_DIR,
                    mcp_command=(
                        sys.executable,
                        "-m",
                        "sparkforge_aws.adapters.mcp",
                        "--transport",
                        "stdio",
                    ),
                    mcp_server_name="sparkforge-aws",
                    mcp_verify_tool="sparkforge_aws_runtime_detect",
                )
            )
        )
    overall = st["status"]
    if any(c["status"] == "FAIL" for c in checks):
        overall = "degraded" if st["ledger_entries"] else "broken"
    return {
        "schema": kit.SCHEMA_HEALTH,
        "forge_id": FORGE_ID,
        "status": overall,
        "checks": checks,
        "scope": scope,
        "target_root": st["target_root"],
        "checked_at": kit._utc_now(),
        "repair_hint": "sparkforge-aws repair"
        if any(c.get("repairable") for c in checks)
        else None,
    }


def repair(
    *,
    scope: str = "project",
    root: Path | None = None,
    cwd: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Regrava assets gerenciados que sumiram ou foram tocados por engano.
    Arquivo do usuario (sha divergente e nao gerenciado) nunca e tocado."""
    spec = _spec()
    cwd = Path(cwd or Path.cwd())
    target = kit.resolve_scope(spec, scope, cwd, root)
    content = _content_root()
    disco = writer.Disco(target, dry_run=dry_run)
    manifesto = writer.load_manifest(target)
    fixed, skipped = [], []
    for rel, reg in sorted((manifesto.get("files") or {}).items()):
        caminho = disco.local(rel)
        dados = disco.ler(caminho)
        drifted = dados is None or writer.sha256_bytes(dados) != reg.get("sha256")
        if not drifted or reg.get("marker"):
            continue
        # re-render e compara: so regrava se o conteudo canonico difere
        regenerado = None
        for nome in manifesto.get("hosts", {}):
            h = project_host(nome, target)
            for d, b in project_plan(h, content, target):
                if disco.chave(d) == rel:
                    regenerado = b
                    break
            if regenerado is not None:
                break
        if regenerado is None:
            skipped.append(rel)
            continue
        if dados is not None and dados != regenerado and not reg.get("owners"):
            skipped.append(rel)  # arquivo do usuario, nunca nosso
            continue
        disco.gravar(caminho, regenerado)
        reg["sha256"] = writer.sha256_bytes(regenerado)
        fixed.append(rel)
    # Configs gerenciados (.mcp.json): restaura com a `entry` gravada no
    # registro — reproduz exatamente o que o install escreveu, inclusive o
    # gateway-profile. Drift cobre: arquivo ausente, entrada ausente no JSON e
    # entrada divergente. Entrada editada pelo usuario recusa
    # `editado_pelo_usuario` -> skipped, nunca regravado. Sem `entry`
    # (manifesto antigo): nao da para reproduzir com certeza -> skipped.
    vistos_cfg: set[str] = set()
    for nome in sorted(manifesto.get("hosts") or {}):
        for reg in manifesto["hosts"][nome].get("config") or []:
            rel = reg["path"]
            if rel in vistos_cfg or reg.get("format") != "json":
                continue
            vistos_cfg.add(rel)
            caminho = disco.local(rel)
            entrada = reg.get("entry")
            if entrada is None:
                skipped.append(rel)
                continue
            dados = disco.ler(caminho)
            doc = None
            if dados is not None:
                try:
                    doc = json.loads(dados.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    skipped.append(rel)  # JSON do usuario ilegivel
                    continue
            servidores = (doc.get("mcpServers") or {}) if isinstance(doc, dict) else {}
            atual = next((servidores[k] for k in writer._SERVIDOR_KEYS if k in servidores), None)
            if atual is not None and writer._sha_entrada(atual) == reg.get("entry_sha256"):
                continue  # entrada intacta: nada a reparar
            out = writer.apply_json_config(nome, caminho, entrada, disco=disco, manifesto=manifesto)
            (fixed if out["status"] == "written" else skipped).append(rel)
    docs_check: dict[str, Any] | None = None
    if not dry_run:
        writer.save_manifest(target, manifesto)
        # Blocos `forge:*` dos consumer docs: re-assert determinístico a
        # partir dos manifests em `.forge/context/` — nunca toca conteúdo
        # do usuário fora dos marcadores; marcador ambíguo recusa nomeado.
        try:
            out_docs = fctx.repair_docs(target, legacy_tags=_LEGACY_DOC_TAGS)
            fixed.extend(f"docs:{w}" for w in out_docs["written"])
            docs_check = {
                "id": "consumer-docs",
                "status": "PASS",
                "detail": f"{out_docs['status']} ({len(out_docs['written'])} writes)",
            }
        except fctx.ContextError as exc:
            skipped.append(f"docs:{exc.kind}")
            docs_check = {
                "id": "consumer-docs",
                "status": "BLOCKED",
                "detail": f"{exc.kind}: {exc.detail}",
            }
    checks = [
        {
            "id": "repair",
            "status": "PASS" if not skipped else "FAIL",
            "detail": f"{len(fixed)} restored, {len(skipped)} skipped",
        }
    ]
    if docs_check is not None:
        checks.append(docs_check)
    return _receipt(
        "repair",
        scope,
        target,
        "recommended",
        managed=[],
        checks=checks,
        repaired=fixed,
        skipped=skipped,
        status="completed" if not skipped else "failed",
    )


def uninstall(
    *,
    scope: str = "project",
    host: str = "all",
    root: Path | None = None,
    cwd: Path | None = None,
    purge: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    if scope == "user":
        from sparkforge_aws.integrate import detach as _detach

        return _detach(host, home=Path.home(), dry_run=dry_run)
    spec = _spec()
    cwd = Path(cwd or Path.cwd())
    target = kit.resolve_scope(spec, scope, cwd, root)
    state = kit.state_dir_for(spec, scope, target)
    disco = writer.Disco(target, dry_run=dry_run)
    manifesto = writer.load_manifest(target)
    nomes = _hosts_for(host)
    removed, kept = [], []
    with kit.acquire_lock(state):
        for nome in nomes:
            relativos = writer.host_files(manifesto, nome)
            out = writer.remove_owned(disco, manifesto, nome, relativos)
            removed += out["removed"]
            kept += out["kept_shared"] + out["kept_preexisting"]
            # tira a entrada mcpServers do .mcp.json se foi a ultima do host
            h = project_host(nome, target)
            if h.mcp_config is not None:
                cfg = next(
                    (
                        r
                        for r in (manifesto.get("hosts") or {}).get(nome, {}).get("config", [])
                        if r.get("path") == ".mcp.json"
                    ),
                    None,
                )
                if cfg:
                    _mcp_unset(disco, manifesto, nome, h.mcp_config)
        # blocos `forge:*` + legado: removidos pela camada de docs depois do
        # unregister (protocolo regen sem nos); entradas de ledger antigas
        # dos 3 docs sao descartadas — o arquivo nao e mais file-asset nosso.
        for doc_name in _CONSUMER_DOCS:
            manifesto.get("files", {}).pop(disco.chave(target / doc_name), None)
        context_checks: list[dict[str, Any]] = []
        if not dry_run:
            writer.save_manifest(target, manifesto)
            _prune_empty(target, removed)
            # Só chama a camada de contexto quando há resíduo — ambas as
            # ops adquirem lock e criariam `.forge/context/` num root
            # pristino.
            if _docs_leftovers(target):
                context_checks = [
                    _unregister_context(target), _uninstall_docs(target)]
    receipt = _receipt(
        "uninstall",
        scope,
        target,
        "recommended",
        managed=[],
        checks=[{"id": "uninstall", "status": "PASS", "detail": f"{len(removed)} removed"}]
        + context_checks,
        removed=removed,
        kept=kept,
        status="completed",
    )
    if not dry_run:
        _write_receipt(state, receipt)
        if purge:
            _purge_state(state)
    return receipt


def _prune_empty(target: Path, removed: list[str]) -> None:
    """Apaga diretorios esvaziados pelo uninstall, subindo ate (sem incluir)
    `target`. Diretorio vazio nao carrega conteudo do usuario."""
    seen: set[str] = set()
    for rel in sorted(removed, key=len, reverse=True):
        d = (target / rel).parent
        while d != target and target in d.parents and d.is_dir():
            if str(d) in seen or any(d.iterdir()):
                break
            seen.add(str(d))
            d.rmdir()
            d = d.parent


def _mcp_unset(disco: writer.Disco, manifesto: dict[str, Any], nome: str, caminho: Path) -> None:
    dados = disco.ler(caminho)
    if dados is None:
        return
    try:
        doc = json.loads(dados.decode("utf-8"))
    except ValueError:
        return
    servidores = doc.get("mcpServers") or {}
    for k in ("sparkforge-aws", "sparkforge", "sparkforge_aws"):
        servidores.pop(k, None)
    if servidores:
        doc["mcpServers"] = servidores
    else:
        doc.pop("mcpServers", None)
    if doc:
        disco.gravar(caminho, (json.dumps(doc, indent=2) + "\n").encode("utf-8"))
    else:
        disco.apagar(caminho)
    hosts = manifesto.get("hosts") or {}
    hosts.get(nome, {})["config"] = [
        r for r in hosts.get(nome, {}).get("config", []) if r.get("path") != ".mcp.json"
    ]


def _purge_state(state: Path) -> None:
    import shutil

    shutil.rmtree(state, ignore_errors=True)


# --------------------------------------------------------------------------
# update + mcp verify
# --------------------------------------------------------------------------


def update(
    *, to: str | None = None, repo: Path | None = None, dry_run: bool = False
) -> dict[str, Any]:
    """Atualiza o runtime instalado pelo bootstrap (venv em
    ~/.forge/installs/) ou instala a partir do checkout.

    `--to` nunca aceita 'latest': a versao e sempre pinned."""
    manifest = _installation_manifest()
    checks: list[dict[str, Any]] = []
    if to == "latest":
        return _receipt(
            "update",
            "user",
            Path.home(),
            "recommended",
            managed=[],
            checks=[{"id": "version", "status": "FAIL", "detail": "'latest' nunca e instalavel"}],
            status="failed",
        )
    src_path = (manifest.get("source") or {}).get("path")
    src = repo or (Path(src_path) if src_path else None)
    if src is None or not src.exists():
        return _receipt(
            "update",
            "user",
            Path.home(),
            "recommended",
            managed=[],
            checks=[
                {
                    "id": "source",
                    "status": "BLOCKED",
                    "detail": "sem checkout registrado — instale pelo setup",
                }
            ],
            status="failed",
        )
    if manifest.get("venv"):
        venv_py = Path(manifest["venv"])
        venv_py = venv_py / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if not venv_py.exists():
            checks.append(
                {"id": "venv", "status": "FAIL", "detail": f"venv {manifest['venv']} incompleta"}
            )
            return _receipt(
                "update",
                "user",
                Path.home(),
                "recommended",
                managed=[],
                checks=checks,
                status="failed",
            )
        cmd = [str(venv_py), "-m", "pip", "install", "--upgrade", str(src)]
        if dry_run:
            return _receipt(
                "update",
                "user",
                Path.home(),
                "recommended",
                managed=[],
                checks=[{"id": "pip", "status": "UNVERIFIED", "detail": " ".join(cmd)}],
                status="planned",
            )
        import subprocess

        r = subprocess.run(  # noqa: S603 — venv python + fixed pip args
            cmd, capture_output=True, text=True, timeout=900
        )
        checks.append(
            {
                "id": "pip",
                "status": "PASS" if r.returncode == 0 else "FAIL",
                "detail": (r.stdout or r.stderr)[-300:],
            }
        )
        return _receipt(
            "update",
            "user",
            Path.home(),
            "recommended",
            managed=[],
            checks=checks,
            status="completed" if r.returncode == 0 else "failed",
        )
    checks.append(
        {
            "id": "source",
            "status": "UNVERIFIED",
            "detail": "sem venv registrada; rode scripts/forge_bootstrap.py",
        }
    )
    return _receipt(
        "update", "user", Path.home(), "recommended", managed=[], checks=checks, status="failed"
    )


def mcp_verify() -> dict[str, Any]:
    return kit.mcp_verify(_spec())


# --------------------------------------------------------------------------
# contract docs
# --------------------------------------------------------------------------


def _receipt(
    operation: str,
    scope: str,
    target: Path,
    profile: str,
    *,
    managed: list,
    checks: list,
    markers: list | None = None,
    refused: list | None = None,
    repaired: list | None = None,
    skipped: list | None = None,
    removed: list | None = None,
    kept: list | None = None,
    dry_run: bool = False,
    status: str = "completed",
) -> dict[str, Any]:
    verification = (
        "PASS"
        if all(c["status"] in ("PASS", "NOT_APPLICABLE", "UNVERIFIED") for c in checks)
        else "FAIL"
    )
    seed = json.dumps(
        {"o": operation, "t": str(target), "ts": kit._utc_now()}, sort_keys=True
    ).encode()
    doc = {
        "schema": kit.SCHEMA_RECEIPT,
        "receipt_id": f"sha256:{kit._sha(seed)}",
        "forge_id": FORGE_ID,
        "operation": operation,
        "scope": scope,
        "target_root": str(target),
        "profile": profile,
        "dry_run": dry_run,
        "managed_files": managed,
        "managed_markers": markers or [],
        "checks": checks,
        "verification": {"status": verification},
        "status": status,
        "created_at": kit._utc_now(),
        "created_by": f"{DIST}/{__version__}",
    }
    for k, v in (
        ("refused", refused),
        ("repaired", repaired),
        ("skipped", skipped),
        ("removed", removed),
        ("kept", kept),
    ):
        if v is not None:
            doc[k] = v
    return doc


def _write_receipt(state: Path, receipt: dict[str, Any]) -> Path:
    ts = kit._utc_now().replace(":", "").replace("-", "")
    path = state / RECEIPTS_DIR / f"{receipt['operation']}-{ts}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_workspace_doc(scope: str, target: Path, receipt: dict[str, Any]) -> None:
    if scope != "workspace":
        return
    doc = {
        "schema": kit.SCHEMA_WORKSPACE,
        "workspace_root": str(target),
        "projects": [
            {
                "path": str(target),
                "forge_id": FORGE_ID,
                "receipt_id": receipt["receipt_id"],
                "installed_at": receipt["created_at"],
            }
        ],
        "created_at": receipt["created_at"],
        "updated_at": receipt["created_at"],
    }
    path = target / STATE_DIR / "workspace-install.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _installation_manifest() -> dict[str, Any]:
    path = kit.installations_dir() / f"{FORGE_ID}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _register(target: Path) -> None:
    """Atualiza `~/.forge/installations/spark-forge-aws.json` quando o
    bootstrap ja o escreveu (o runtime instalado e a autoridade); senao,
    grava um manifesto minimo apontando para o estado do projeto."""
    existing = _installation_manifest()
    doc = dict(existing) if existing else {}
    doc.update(
        {
            "schema": kit.SCHEMA_MANIFEST,
            "forge_id": FORGE_ID,
            "package": PACKAGE,
            "distribution": DIST,
            "cli": {"name": CLI, "version_cmd": [CLI, "--version"]},
            "version": __version__,
            "updated_at": kit._utc_now(),
            "installed_at": doc.get("installed_at", kit._utc_now()),
            "installed_by": doc.get(
                "installed_by", {"agent": f"{DIST}-cli", "version": __version__}
            ),
            "source": doc.get("source", {"kind": "project-install", "path": str(target)}),
        }
    )
    doc.setdefault("install_root", str(kit.installs_root() / FORGE_ID))
    doc.setdefault(
        "mcp",
        {
            "server_name": "sparkforge-aws",
            "command": ["sparkforge-aws", "mcp", "serve"],
            "verified": False,
        },
    )
    kit.register_installation(doc)


# --------------------------------------------------------------------------
# forge-context/v1 wiring (install-2.0 ciclo 2, the-forge ADR-0061)
# `.forge/context/` e o registry de workspace compartilhado entre forges —
# camada diferente de `~/.forge/installations/` (conta) e de
# `.sparkforge_aws/integrations.json` (ledger de posse). Este forge so
# registra e desregistra o proprio `forge_id`.
# --------------------------------------------------------------------------

_PKG_DIR = Path(__file__).resolve().parents[1]
_REPO_DIR = _PKG_DIR.parent

_AWS_DOMAINS: tuple[str, ...] = (
    "pyspark",
    "aws-glue",
    "amazon-emr",
    "amazon-athena",
    "apache-iceberg",
    "spark-streaming",
    "terraform",
    "data-quality",
)


def _bundled_dir(name: str) -> Path | None:
    """`rules/catalog`/`knowledge` moram na raiz do clone e entram no wheel
    via force-include (mesmo padrao do integrate/bundle)."""
    for cand in (_REPO_DIR / name, _PKG_DIR / name):
        if cand.is_dir():
            return cand
    return None


def _mds(base: Path) -> list[str]:
    return sorted(p.stem for p in base.glob("*.md"))


def _context_manifest(
    *, scope: str, profile: str, hosts: list[str], components: dict[str, Any] | None
) -> dict[str, Any]:
    """Manifesto forge/context/v1 montado das fontes reais: `forge.json` +
    `forge.agentic.json` + `manifest.json` no checkout (quando presente) e
    as raizes bundled de skills/agents/rules/knowledge que o install usou."""
    forge_json = kit._load_json(_REPO_DIR / "forge.json", None)
    forge_json = forge_json if isinstance(forge_json, dict) else None
    agentic = kit._load_json(_REPO_DIR / "forge.agentic.json", None)
    agentic = agentic if isinstance(agentic, dict) else None
    manifest_json = kit._load_json(_REPO_DIR / "manifest.json", None)
    manifest_json = manifest_json if isinstance(manifest_json, dict) else None

    skills: list[str] = []
    coordinators: list[str] = []
    executors: list[str] = []
    try:
        content = sources.content_root()
    except sources.SourcesError:
        content = None
    if content is not None:
        skills = sorted(d.name for d in (content / "skills").iterdir() if d.is_dir())
        agents_root = content / "agents"
        if agents_root.is_dir():
            coordinators = _mds(agents_root)
            executors = _mds(agents_root / "executors")

    rules_dir = _bundled_dir("rules/catalog")
    rule_areas = sorted(p.stem for p in rules_dir.glob("*.yaml")) if rules_dir else []
    knowledge_dir = _bundled_dir("knowledge")
    providers: list[dict[str, Any]] = []
    if knowledge_dir is not None:
        providers.append(
            {
                "id": "knowledge-base",
                "interface": "bundled",
            }
        )
    evals_dir = _bundled_dir("evals")
    eval_suites = [
        {"id": p.name, "kind": "output-verification"}
        for p in sorted(evals_dir.iterdir())
        if p.is_dir()
    ] if evals_dir else []

    checks: list[dict[str, Any]] = [
        {
            "id": "skills-bundle",
            "status": "PASS" if skills else "UNVERIFIED",
            "detail": f"{len(skills)} skills",
        },
        {
            "id": "agent-specs",
            "status": "PASS" if coordinators else "UNVERIFIED",
            "detail": f"{len(coordinators)} coordinators, {len(executors)} executors",
        },
        {
            "id": "rules-catalog",
            "status": "PASS" if rule_areas else "UNVERIFIED",
            "detail": f"{len(rule_areas)} rule files",
        },
    ]
    return fctx.build_manifest(
        forge_id=FORGE_ID,
        name="Spark Forge AWS",
        version=__version__,
        cli=CLI,
        package=PACKAGE,
        distribution=DIST,
        python_spec=PYTHON_SPEC,
        scope=scope,
        profile=profile,
        hosts=hosts,
        forge_json=forge_json,
        agentic=agentic,
        domains=_AWS_DOMAINS,
        skills=skills,
        coordinators=coordinators,
        agents=executors,
        rule_areas=rule_areas,
        knowledge_providers=providers,
        eval_suites=eval_suites,
        protocols=(
            {"id": "forge/v1", "version": "1"},
            {"id": "forge/context/v1", "version": "1"},
            {"id": "forge/context-registry/v1", "version": "1"},
        ),
        discovery_commands=(
            {
                "id": "analyze-pyspark",
                "argv": [CLI, "analyze", "pyspark", "--path", "{target}"],
                "mode": "direct-capability",
                "read_only": True,
                "description": "static AST analysis of PySpark sources",
            },
            {
                "id": "next-step",
                "argv": [CLI, "next-step"],
                "mode": "specialist-workflow",
                "read_only": True,
                "description": "routing.yaml driven coordinator recommendation",
            },
            {
                "id": "playbook",
                "argv": [CLI, "playbook", "spark-performance-architect", "--repo", "{target}"],
                "mode": "specialist-workflow",
                "read_only": True,
                "description": "coordinator decomposition playbook",
            },
            {
                "id": "doctor",
                "argv": [CLI, "doctor"],
                "mode": "diagnostic-only",
                "read_only": True,
                "description": "environment + installation health",
            },
        ),
        mcp={
            "server_name": "sparkforge-aws",
            "command": [CLI, "mcp", "serve"],
            "verify_tool": "sparkforge_aws_runtime_detect",
        },
        resources={
            "skills-bundle": {
                "kind": "bundled",
                "location": "sparkforge_aws/integrate/bundle/skills",
                "optional": False,
            },
            "agents-bundle": {
                "kind": "bundled",
                "location": "sparkforge_aws/integrate/bundle/agents",
                "optional": False,
            },
            "rules-catalog": {
                "kind": "bundled",
                "location": "sparkforge_aws/rules/catalog",
                "optional": False,
            },
            "knowledge-base": {
                "kind": "bundled",
                "location": "sparkforge_aws/knowledge",
                "optional": False,
            },
            "integration-ledger": {
                "kind": "referenced",
                "location": ".sparkforge_aws/integrations.json",
                "optional": True,
            },
            "install-state": {
                "kind": "referenced",
                "location": ".sparkforge_aws/install",
                "optional": True,
            },
        },
        mutating_verbs=(
            "install",
            "uninstall",
            "repair",
            "integrate",
            "detach",
            "collect",
            "case update",
        ),
        requires_approval=("install", "uninstall", "integrate", "detach"),
        offline_available=True,
        health={
            "status": "healthy" if skills and coordinators and rule_areas else "degraded",
            "checks": checks,
        },
        components=components,
        recorded_by=DIST,
    )


def _register_context(
    target: Path,
    receipt: dict[str, Any],
    *,
    scope: str,
    profile: str,
    hosts: list[str],
    components: dict[str, Any] | None,
) -> None:
    """Grava `.forge/context/` — manifesto de capacidades + entrada no
    registry + ROUTING.md. Falha de contexto vira check BLOCKED nomeado no
    recibo, nunca erro silencioso nem install falho."""
    try:
        manifest = _context_manifest(
            scope=scope, profile=profile, hosts=hosts, components=components
        )
        out = fctx.register_forge(target, manifest, owner=FORGE_ID)
        receipt.setdefault("checks", []).append(
            {
                "id": "context-registry",
                "status": "PASS",
                "detail": f".forge/context {out['status']} ({len(out['written'])} writes)",
            }
        )
    except fctx.ContextError as exc:
        receipt.setdefault("checks", []).append(
            {"id": "context-registry", "status": "BLOCKED", "detail": f"{exc.kind}: {exc.detail}"}
        )
        return
    try:
        docs = fctx.install_docs(
            target, manifest, owner=FORGE_ID, legacy_tags=_LEGACY_DOC_TAGS
        )
        receipt.setdefault("checks", []).append(
            {
                "id": "consumer-docs",
                "status": "PASS",
                "detail": (
                    f"{docs['status']}: {len(docs['written'])} written, "
                    f"{len(docs['kept'])} kept"
                ),
            }
        )
    except fctx.ContextError as exc:
        receipt.setdefault("checks", []).append(
            {"id": "consumer-docs", "status": "BLOCKED", "detail": f"{exc.kind}: {exc.detail}"}
        )


def _unregister_context(target: Path) -> dict[str, Any]:
    """Remove somente o manifesto/entry deste forge — recusa nomeada se o
    alvo for de outro instalador."""
    try:
        out = fctx.unregister_forge(target, FORGE_ID, owner=FORGE_ID)
        return {
            "id": "context-registry",
            "status": "PASS",
            "detail": f".forge/context {out['status']}",
        }
    except fctx.ContextError as exc:
        return {
            "id": "context-registry",
            "status": "BLOCKED",
            "detail": f"{exc.kind}: {exc.detail}",
        }


def _docs_leftovers(target: Path) -> bool:
    """True quando o alvo ainda carrega resíduo forge_context: dir de
    contexto, nosso bloco managed, o bloco compartilhado do ecossistema,
    o sentinel do protocolo ou um marker legado. Leitura sem lock — só
    um hit justifica o caminho de escrita."""
    if (target / fctx.CONTEXT_DIR).exists():
        return True
    needles = (
        f"forge:{FORGE_ID}:", f"{fctx.DOC_TAG_ECOSYSTEM}:",
        fctx.PROTOCOL_SENTINEL, *_LEGACY_DOC_TAGS,
    )
    for name in _CONSUMER_DOCS:
        path = target / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(n in text for n in needles):
            return True
    return False


def _uninstall_docs(target: Path) -> dict[str, Any]:
    """Retira os blocos `forge:spark-forge-aws` (+ legado) dos consumer docs
    e regenera os documentos compartilhados sem nos. Roda depois de
    ``_unregister_context`` para o protocolo sair sem a nossa seção."""
    try:
        out = fctx.uninstall_docs(
            target, FORGE_ID, owner=FORGE_ID, legacy_tags=_LEGACY_DOC_TAGS
        )
        return {
            "id": "consumer-docs",
            "status": "PASS",
            "detail": f"{out['status']}: {len(out['written'])} changed",
        }
    except fctx.ContextError as exc:
        return {
            "id": "consumer-docs",
            "status": "BLOCKED",
            "detail": f"{exc.kind}: {exc.detail}",
        }


__all__ = [
    "HOSTS",
    "PROFILES",
    "GATEWAY_PROFILES",
    "doctor",
    "install",
    "mcp_verify",
    "repair",
    "status",
    "uninstall",
    "update",
]
