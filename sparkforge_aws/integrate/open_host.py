"""`sparkforge-aws ai` — abre o host de IA quando suportado.

Fluxo real por host, todo passo com comando documentado e verificado nas
versões instaladas (devin 3000.11.3, Claude Code 2.1.295, codex-cli
0.160.0, lidas em 2026-10):

1. detecta o binário (`shutil.which`);
2. lê a versão (`<bin> --version`);
3. confere autenticação pelo subcomando oficial de status — o recibo
   carrega só o booleano `logged_in`, nunca a saída (ela pode listar
   caminhos de credenciais);
4. lê o estado da integração no repo (`install.status`, manifesto +
   `.mcp.json`);
5. com `--launch` e TTY, executa o `<bin>` no diretório do repo — o REPL
   do host herda o terminal e devolve o exit code ao recibo. Sem TTY ou
   sem `--launch`, o recibo traz `launch_command` para o operador colar.

Host deslogado não é lançado: o recibo aponta o comando oficial de login,
sem nunca pedir credencial em prompt.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge_aws.install import lifecycle
from sparkforge_aws.integrate import claude as _claude
from sparkforge_aws.integrate.hosts import FONTES, HOSTS

Runner = _claude.Runner
Which = _claude.Which

LOGIN_HINTS = {
    "devin": "devin auth login",
    "claude": "claude auth login",
    "codex": "codex login",
    "copilot": "copilot",  # o login do copilot acontece dentro do REPL
}


@dataclass(frozen=True)
class _HostCmd:
    binary: str
    auth_status: tuple[str, ...] | None


_HOST_CMDS = {
    "devin": _HostCmd("devin", ("auth", "status")),
    "claude": _HostCmd("claude", ("auth", "status")),
    "codex": _HostCmd("codex", ("login", "status")),
    "copilot": _HostCmd("copilot", None),
}


def _logged_in(host: str, saida: str) -> bool | None:
    """Só o booleano. Sem evidência positiva/negativa legível: `None` (honesto)."""
    if host == "claude":
        try:
            dados = json.loads(saida)
        except ValueError:
            dados = None
        if isinstance(dados, dict) and "loggedIn" in dados:
            return bool(dados["loggedIn"])
    low = saida.lower()
    # negativo antes do positivo: "Not logged in" contem "logged in"
    if any(trecho in low for trecho in (
        "not logged", "logged out", "no credentials", "unauthorized",
    )):
        return False
    if "logged in" in low:
        return True
    return None


def _chamar(executavel: str, argv: list[str], runner: Runner) -> tuple[int, str] | dict[str, Any]:
    try:
        return runner([executavel, *argv])
    except subprocess.TimeoutExpired as erro:
        return {
            "status": "refused",
            "reason": "host_cli_timeout",
            "command": " ".join(argv),
            "timeout_s": erro.timeout,
        }
    except OSError as erro:
        return {
            "status": "refused",
            "reason": "host_cli_falhou",
            "command": " ".join(argv),
            "output": str(erro)[-_claude.SAIDA_MAX:],
        }


def _integracao(repo: Path) -> dict[str, Any]:
    """O estado do install no repo, sem tocar nada — `unverified` quando nunca instalou."""
    try:
        st = lifecycle.status(scope="project", root=repo, cwd=repo)
    except Exception as erro:  # status nunca deve derrubar o fluxo de abrir host
        return {"state": "unknown", "error": str(erro)[:200]}
    return {
        "state": st.get("status", "unknown"),
        "drift_ok": (st.get("drift") or {}).get("ok"),
        "ledger_entries": st.get("ledger_entries"),
    }


def host_state(
    host: str,
    *,
    repo: Path,
    which: Which | None = None,
    runner: Runner | None = None,
) -> dict[str, Any]:
    """Estado observado de um host: binário, versão, auth, integração, comando de abertura."""
    if host not in HOSTS:
        return {"host": host, "state": "refused",
                "reason": "host_desconhecido", "known": list(HOSTS)}
    which = which or _claude.WHICH_PADRAO
    runner = runner or _claude.RUNNER_PADRAO
    cmd = _HOST_CMDS[host]
    estado: dict[str, Any] = {
        "host": host,
        "binary": cmd.binary,
        "fonte": FONTES[host],
        "launch_command": cmd.binary,
    }
    caminho = which(cmd.binary)
    if not caminho:
        estado["state"] = "NOT_DETECTED"
        return estado
    estado["binary_path"] = caminho
    estado["state"] = "DETECTED"

    versao = _chamar(caminho, ["--version"], runner)
    if isinstance(versao, dict):
        estado["version_refused"] = versao
    else:
        rc, saida = versao
        primeira = next(
            (linha.strip() for linha in saida.splitlines() if linha.strip()), "")

        estado["version"] = primeira or None
        estado["state"] = "SUPPORTED" if rc == 0 else "DETECTED"

    if cmd.auth_status is None:
        estado["logged_in"] = None
        estado["auth_note"] = "sem subcomando de status documentado nesta revisão"
    else:
        auth = _chamar(caminho, list(cmd.auth_status), runner)
        if isinstance(auth, dict):
            estado["auth_refused"] = auth
            estado["logged_in"] = None
        else:
            estado["logged_in"] = _logged_in(host, auth[1])
    if estado.get("logged_in") is False:
        estado["login_hint"] = LOGIN_HINTS[host]

    estado["integration"] = _integracao(repo)
    estado["state"] = _estado_final(estado)
    return estado


def _estado_final(estado: dict[str, Any]) -> str:
    if estado.get("logged_in") is False:
        return "NEEDS_LOGIN"
    integ = (estado.get("integration") or {}).get("state")
    if integ == "healthy":
        return "READY"
    if integ in {"degraded", "broken"}:
        return "INTEGRATION_" + integ.upper()
    return "SUPPORTED"


def ai_flow(
    alvo: str,
    *,
    repo: Path,
    launch: bool = False,
    tty: bool | None = None,
    which: Which | None = None,
    runner: Runner | None = None,
    exec_host: Callable[[str, Path], int] | None = None,
) -> dict[str, Any]:
    """O fluxo §1.2: seletor implícito por `alvo` (`all` mede os quatro),
    estado por host, e lançamento real quando `--launch` + TTY + READY.

    `exec_host(caminho, repo)` é o seam do lançamento — o CLI injeta
    `subprocess.call`; o teste injeta um spy. Sem TTY, `launched` é falso e
    `launch_refused` diz por quê — nunca silêncio."""
    repo = Path(repo)
    nomes = list(HOSTS) if alvo == "all" else [alvo]
    estados = [
        host_state(nome, repo=repo, which=which, runner=runner)
        for nome in nomes
    ]
    recibo: dict[str, Any] = {
        "repo": repo.as_posix(),
        "hosts": estados,
        "launched": False,
    }
    if alvo == "all" or not launch:
        if launch:
            recibo["launch_refused"] = "seletor `all` não lança: escolha um host"
        return recibo

    estado = estados[0]
    tty = sys.stdin.isatty() if tty is None else tty
    if estado["state"] == "NOT_DETECTED":
        recibo["launch_refused"] = "host_ausente"
    elif estado["state"] == "NEEDS_LOGIN":
        recibo["launch_refused"] = "login_necessario"
        recibo["login_hint"] = estado.get("login_hint")
    elif not tty:
        recibo["launch_refused"] = "no_tty"
    else:
        # O caminho veio de shutil.which, mesmo nível de confiança de `claude.run`.
        exec_fn = exec_host or (
            lambda caminho, cwd: subprocess.call(  # noqa: S603
                [caminho], cwd=str(cwd)))
        recibo["launched"] = True
        recibo["host_exit_code"] = exec_fn(estado["binary_path"], repo)
    return recibo
