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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge_aws import __version__
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
        forge_id=FORGE_ID, package=PACKAGE, distribution=DIST, cli_name=CLI,
        python_spec=PYTHON_SPEC, state_dir=STATE_DIR,
        mcp_command=(sys.executable, "-m", "sparkforge_aws.adapters.mcp",
                     "--transport", "stdio"),
        mcp_server_name="sparkforge-aws",
        mcp_verify_tool="sparkforge_aws_runtime_detect",
        marker_files=("AGENTS.md", "CLAUDE.md"),
        marker_body=(
            "**Spark Forge AWS** esta instalado neste projeto.\n\n"
            "- MCP: `sparkforge-aws` (chave gerenciada em `.mcp.json`)\n"
            "- Ciclo de vida: `sparkforge-aws status|repair|uninstall`"
        ),
    )


def _content_root() -> Path:
    return sources.content_root()


def _profile_kinds(profile: str) -> tuple[bool, bool]:
    """(skills?, agents?) — minimal nao instala mirrors."""
    return {
        "minimal": (False, False),
        "recommended": (True, False),
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
    if alvo == "all":
        return list(HOSTS)
    if alvo not in HOSTS:
        raise kit.InstallError(kit.E_HOST, f"host {alvo!r}; conhecidos: {list(HOSTS)} + all")
    return [alvo]


def _marker_body() -> str:
    return (
        "**Spark Forge AWS** esta instalado neste projeto.\n\n"
        "- MCP server: `sparkforge-aws` (chave gerenciada em `.mcp.json`)\n"
        "- Skills/agents: mirrors gerenciados nos diretorios de host\n"
        "- Ciclo de vida: `sparkforge-aws status|repair|uninstall`\n\n"
        "Conteudo entre os marcadores `sparkforge-aws:managed` e gerenciado; "
        "o que estiver fora e do usuario."
    )


def install(
    alvo: str = "all",
    *,
    scope: str = "project",
    root: Path | None = None,
    profile: str = "recommended",
    gateway_profile: str | None = None,
    python: str | None = None,
    dry_run: bool = False,
    yes: bool = False,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Instala o Forge no projeto/workspace (ou no HOME via `integrate`)."""
    if profile not in PROFILES:
        raise kit.InstallError(kit.E_PROFILE, f"profile {profile!r}; {PROFILES}")
    if scope == "user":
        return _install_user(alvo, profile, gateway_profile, python, dry_run, yes)

    cwd = Path(cwd or Path.cwd())
    spec = _spec()
    target = kit.resolve_scope(spec, scope, cwd, root)
    state = kit.state_dir_for(spec, scope, target)
    content = _content_root()

    nomes = _hosts_for(alvo)
    disco = writer.Disco(target, dry_run=dry_run)
    manifesto = writer.load_manifest(target)

    if not yes and not dry_run:
        raise kit.InstallError(
            kit.E_NOTAPPROVED,
            "install escreve no projeto; use --yes ou --dry-run")

    with kit.acquire_lock(state):
        plano_total: list[dict[str, Any]] = []
        relatorios: list[dict[str, Any]] = []
        for nome in nomes:
            h = project_host(nome, target)
            skills, agents = _profile_kinds(profile)
            plano = project_plan(h, content, target)
            filtrado = [
                (d, b) for d, b in plano
                if _want_file(d, target, skills, agents)
            ]
            plano_total += [
                {"path": disco.chave(d), "bytes": len(b)} for d, b in filtrado
            ]
            rel = writer.apply_files(
                nome, filtrado, disco=disco, manifesto=manifesto,
                version=__version__)
            configs = []
            if h.mcp_config is not None:
                configs.append(
                    writer.apply_json_config(
                        nome, h.mcp_config,
                        mcp_entry(nome, python or sys.executable,
                                  profile=gateway_profile),
                        disco=disco, manifesto=manifesto))
            rel["config"] = configs
            relatorios.append(rel)

        # Bloco gerenciado em AGENTS.md (CLAUDE.md so se ja existir).
        markers = []
        for marker_file in ("AGENTS.md", "CLAUDE.md"):
            alvo_m = target / marker_file
            if not alvo_m.exists() and marker_file != "AGENTS.md":
                continue
            original = alvo_m.read_text(encoding="utf-8") if alvo_m.exists() else ""
            updated = kit.apply_marker_block(original, "sparkforge-aws",
                                             _marker_body())
            if updated != original:
                disco.gravar(alvo_m, updated.encode("utf-8"))
            markers.append({"file": marker_file, "marker": "sparkforge-aws",
                            "sha256": kit.marker_sha("sparkforge-aws",
                                                     _marker_body())})
            chave = disco.chave(alvo_m)
            manifesto["files"].setdefault(
                chave, {"sha256": kit._sha(updated.encode()), "owners": [],
                        "marker": True})

        escritos = sum(len(r.get("written") or []) for r in relatorios)
        removidos = sum(len(r.get("removed") or []) for r in relatorios)
        recusas = [
            {"host": r["host"], **rec}
            for r in relatorios for rec in (r.get("refused") or [])
        ]
        for r in relatorios:
            for c in r.get("config") or []:
                if c["status"] == "refused":
                    recusas.append({"host": r["host"], "reason": c["reason"],
                                    "path": c["path"]})
        if not dry_run:
            writer.save_manifest(target, manifesto)

    receipt = _receipt(
        "install", scope, target, profile,
        managed=[{"path": f["path"], "sha256": "",
                  "kind": "skill" if "skills" in f["path"] else "agent",
                  "action": "written"} for f in plano_total],
        markers=markers,
        checks=[{"id": "files", "status": "PASS",
                 "detail": f"{escritos} written, {removidos} removed"},
                {"id": "refusals", "status": "PASS" if not recusas else "FAIL",
                 "detail": f"{len(recusas)} refused"}],
        refused=recusas, dry_run=dry_run,
        status="planned" if dry_run else ("completed" if not recusas else "failed"),
    )
    if not dry_run:
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
    return (skills if is_skill else agents)


def _install_user(alvo: str, profile: str, gateway_profile: str | None,
                  python: str | None, dry_run: bool, yes: bool) -> dict[str, Any]:
    """Escopo `user` = `integrate` existente (HOME)."""
    from sparkforge_aws.integrate import integrate as _integrate

    if not yes and not dry_run:
        raise kit.InstallError(
            kit.E_NOTAPPROVED,
            "install --scope user escreve no HOME; use --yes ou --dry-run")
    out = _integrate(
        alvo, home=Path.home(), dry_run=dry_run,
        profile=gateway_profile if gateway_profile in GATEWAY_PROFILES else None,
        python=python,
    )
    out["profile"] = profile
    out["scope"] = "user"
    return out


# --------------------------------------------------------------------------
# status / doctor / repair / uninstall
# --------------------------------------------------------------------------

def status(*, scope: str = "project", root: Path | None = None,
           cwd: Path | None = None) -> dict[str, Any]:
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
    ok = sum(1 for d in drift if d["status"] == "ok")
    bad = [d for d in drift if d["status"] != "ok"]
    return {
        "schema": kit.SCHEMA_HEALTH, "forge_id": FORGE_ID,
        "scope": scope, "target_root": str(target),
        "state_dir": str(target / STATE_DIR),
        "ledger_entries": len(files),
        "drift": {"ok": ok,
                  "modified": [d for d in bad if d["status"] == "modified"],
                  "missing": [d for d in bad if d["status"] == "missing"]},
        "hosts": {n: sorted(writer.host_files(manifesto, n))
                  for n in manifesto.get("hosts", {})},
        "status": ("healthy" if files and not bad else
                   "degraded" if ok else
                   "unverified" if not files else "broken"),
        "checked_at": kit._utc_now(),
    }


def doctor(*, scope: str = "project", root: Path | None = None,
           cwd: Path | None = None) -> dict[str, Any]:
    st = status(scope=scope, root=root, cwd=cwd)
    checks: list[dict[str, Any]] = [{
        "id": "install-state", "status": st["status"].upper(),
        "detail": f"{st['ledger_entries']} ledger entries"}]
    checks += [{"id": f"drift:{d['path']}", "status": "FAIL",
                "detail": d["status"], "repairable": True}
               for d in st["drift"]["modified"] + st["drift"]["missing"]]
    import importlib.util
    if importlib.util.find_spec("mcp") is None:
        checks.append({"id": "mcp-handshake", "status": "UNVERIFIED",
                       "detail": "extra 'mcp' nao instalada — handshake nao testado"})
    else:
        checks.append(kit.mcp_verify(kit.ForgeSpec(
            forge_id=FORGE_ID, package=PACKAGE, distribution=DIST, cli_name=CLI,
            python_spec=PYTHON_SPEC, state_dir=STATE_DIR,
            mcp_command=(sys.executable, "-m", "sparkforge_aws.adapters.mcp",
                         "--transport", "stdio"),
            mcp_server_name="sparkforge-aws",
            mcp_verify_tool="sparkforge_aws_runtime_detect")))
    overall = st["status"]
    if any(c["status"] == "FAIL" for c in checks):
        overall = "degraded" if st["ledger_entries"] else "broken"
    return {"schema": kit.SCHEMA_HEALTH, "forge_id": FORGE_ID,
            "status": overall, "checks": checks,
            "scope": scope, "target_root": st["target_root"],
            "checked_at": kit._utc_now(),
            "repair_hint": "sparkforge-aws repair" if any(
                c.get("repairable") for c in checks) else None}


def repair(*, scope: str = "project", root: Path | None = None,
           cwd: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
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
    if not dry_run:
        writer.save_manifest(target, manifesto)
    return _receipt("repair", scope, target, "recommended",
                    managed=[], checks=[{"id": "repair",
                                         "status": "PASS" if not skipped else "FAIL",
                                         "detail": f"{len(fixed)} restored, "
                                                   f"{len(skipped)} skipped"}],
                    repaired=fixed, skipped=skipped,
                    status="completed" if not skipped else "failed")


def uninstall(*, scope: str = "project", host: str = "all",
              root: Path | None = None, cwd: Path | None = None,
              purge: bool = False, dry_run: bool = False) -> dict[str, Any]:
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
                cfg = next((r for r in
                            (manifesto.get("hosts") or {}).get(nome, {}).get("config", [])
                            if r.get("path") == ".mcp.json"), None)
                if cfg:
                    _mcp_unset(disco, manifesto, nome, h.mcp_config)
        # marcadores
        for marker_file in ("AGENTS.md", "CLAUDE.md"):
            alvo_m = target / marker_file
            if not alvo_m.exists():
                continue
            txt = kit.remove_marker_block(
                alvo_m.read_text(encoding="utf-8"), "sparkforge-aws")
            if txt != alvo_m.read_text(encoding="utf-8"):
                if txt.strip():
                    disco.gravar(alvo_m, txt.encode())
                    kept.append(marker_file)
                else:
                    disco.apagar(alvo_m)
                    removed.append(marker_file)
            manifesto.get("files", {}).pop(disco.chave(alvo_m), None)
        if not dry_run:
            writer.save_manifest(target, manifesto)
            _prune_empty(target, removed)
    receipt = _receipt("uninstall", scope, target, "recommended",
                       managed=[], checks=[{"id": "uninstall",
                                            "status": "PASS",
                                            "detail": f"{len(removed)} removed"}],
                       removed=removed, kept=kept, status="completed")
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


def _mcp_unset(disco: writer.Disco, manifesto: dict[str, Any],
               nome: str, caminho: Path) -> None:
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
        r for r in hosts.get(nome, {}).get("config", [])
        if r.get("path") != ".mcp.json"]


def _purge_state(state: Path) -> None:
    import shutil
    shutil.rmtree(state, ignore_errors=True)


# --------------------------------------------------------------------------
# update + mcp verify
# --------------------------------------------------------------------------

def update(*, to: str | None = None, repo: Path | None = None,
           dry_run: bool = False) -> dict[str, Any]:
    """Atualiza o runtime instalado pelo bootstrap (venv em
    ~/.forge/installs/) ou instala a partir do checkout.

    `--to` nunca aceita 'latest': a versao e sempre pinned."""
    manifest = _installation_manifest()
    checks: list[dict[str, Any]] = []
    if to == "latest":
        return _receipt("update", "user", Path.home(), "recommended",
                        managed=[], checks=[{
                            "id": "version", "status": "FAIL",
                            "detail": "'latest' nunca e instalavel"}],
                        status="failed")
    src_path = (manifest.get("source") or {}).get("path")
    src = repo or (Path(src_path) if src_path else None)
    if src is None or not src.exists():
        return _receipt("update", "user", Path.home(), "recommended",
                        managed=[], checks=[{
                            "id": "source", "status": "BLOCKED",
                            "detail": "sem checkout registrado — instale pelo setup"}],
                        status="failed")
    if manifest.get("venv"):
        venv_py = Path(manifest["venv"])
        venv_py = venv_py / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if not venv_py.exists():
            checks.append({"id": "venv", "status": "FAIL",
                           "detail": f"venv {manifest['venv']} incompleta"})
            return _receipt("update", "user", Path.home(), "recommended",
                            managed=[], checks=checks, status="failed")
        cmd = [str(venv_py), "-m", "pip", "install", "--upgrade", str(src)]
        if dry_run:
            return _receipt("update", "user", Path.home(), "recommended",
                            managed=[], checks=[{"id": "pip", "status": "UNVERIFIED",
                                                 "detail": " ".join(cmd)}],
                            status="planned")
        import subprocess
        r = subprocess.run(  # noqa: S603 — venv python + fixed pip args
            cmd, capture_output=True, text=True, timeout=900)
        checks.append({"id": "pip", "status": "PASS" if r.returncode == 0 else "FAIL",
                       "detail": (r.stdout or r.stderr)[-300:]})
        return _receipt("update", "user", Path.home(), "recommended",
                        managed=[], checks=checks,
                        status="completed" if r.returncode == 0 else "failed")
    checks.append({"id": "source", "status": "UNVERIFIED",
                   "detail": "sem venv registrada; rode scripts/forge_bootstrap.py"})
    return _receipt("update", "user", Path.home(), "recommended",
                    managed=[], checks=checks, status="failed")


def mcp_verify() -> dict[str, Any]:
    return kit.mcp_verify(_spec())


# --------------------------------------------------------------------------
# contract docs
# --------------------------------------------------------------------------

def _receipt(operation: str, scope: str, target: Path, profile: str,
             *, managed: list, checks: list, markers: list | None = None,
             refused: list | None = None, repaired: list | None = None,
             skipped: list | None = None, removed: list | None = None,
             kept: list | None = None, dry_run: bool = False,
             status: str = "completed") -> dict[str, Any]:
    verification = "PASS" if all(
        c["status"] in ("PASS", "NOT_APPLICABLE", "UNVERIFIED")
        for c in checks) else "FAIL"
    seed = json.dumps({"o": operation, "t": str(target),
                       "ts": kit._utc_now()}, sort_keys=True).encode()
    doc = {
        "schema": kit.SCHEMA_RECEIPT,
        "receipt_id": f"sha256:{kit._sha(seed)}",
        "forge_id": FORGE_ID, "operation": operation, "scope": scope,
        "target_root": str(target), "profile": profile, "dry_run": dry_run,
        "managed_files": managed, "managed_markers": markers or [],
        "checks": checks,
        "verification": {"status": verification},
        "status": status,
        "created_at": kit._utc_now(), "created_by": f"{DIST}/{__version__}",
    }
    for k, v in (("refused", refused), ("repaired", repaired),
                 ("skipped", skipped), ("removed", removed), ("kept", kept)):
        if v is not None:
            doc[k] = v
    return doc


def _write_receipt(state: Path, receipt: dict[str, Any]) -> Path:
    ts = kit._utc_now().replace(":", "").replace("-", "")
    path = state / RECEIPTS_DIR / f"{receipt['operation']}-{ts}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def _write_workspace_doc(scope: str, target: Path, receipt: dict[str, Any]) -> None:
    if scope != "workspace":
        return
    doc = {
        "schema": kit.SCHEMA_WORKSPACE, "workspace_root": str(target),
        "projects": [{"path": str(target), "forge_id": FORGE_ID,
                      "receipt_id": receipt["receipt_id"],
                      "installed_at": receipt["created_at"]}],
        "created_at": receipt["created_at"],
        "updated_at": receipt["created_at"],
    }
    path = target / STATE_DIR / "workspace-install.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


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
    doc.update({
        "schema": kit.SCHEMA_MANIFEST, "forge_id": FORGE_ID,
        "package": PACKAGE, "distribution": DIST,
        "cli": {"name": CLI, "version_cmd": [CLI, "--version"]},
        "version": __version__,
        "updated_at": kit._utc_now(),
        "installed_at": doc.get("installed_at", kit._utc_now()),
        "installed_by": doc.get("installed_by",
                                {"agent": f"{DIST}-cli", "version": __version__}),
        "source": doc.get("source", {"kind": "project-install",
                                     "path": str(target)}),
    })
    doc.setdefault("install_root",
                   str(kit.installs_root() / FORGE_ID))
    doc.setdefault("mcp", {"server_name": "sparkforge-aws",
                           "command": ["sparkforge-aws", "mcp", "serve"],
                           "verified": False})
    kit.register_installation(doc)


__all__ = ["HOSTS", "PROFILES", "GATEWAY_PROFILES", "doctor", "install",
           "mcp_verify", "repair", "status", "uninstall", "update"]
