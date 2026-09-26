"""Claude Code: o plugin por marketplace local (D8).

Monta em `~/.sparkforge/claude/` o marketplace `sparkforge-local`, com o plugin
`sparkforge-aws` em `plugins/sparkforge-aws/` (skills, agents, `.mcp.json` e
`.claude-plugin/plugin.json`), e o registra pelo proprio CLI do Claude:

    claude plugin marketplace add <dir> --scope user
    claude plugin install sparkforge-aws@sparkforge-local --scope user --json

Os flags foram conferidos no `--help` do Claude Code 2.1.283. `~/.claude/settings.json`
nao e editado a mao: e formato interno do Claude, e muda sem aviso.

Sem `-y`: pelo `--help` (2.1.283), o `-y` de `install`/`update` so aceita o comando
declarado por um marketplace (plugin instalado por comando, ou `headersHelper`), e o
de `uninstall` so confirma o `--prune`. O plugin local nao tem comando declarado, e
nenhum dos tres pede confirmacao sem TTY. O executor roda com `stdin` fechado e
`TIMEOUT_S`: um prompt inesperado sai como recusa, nunca como espera sem fim.

Cada passo confere antes pelo `list --json` (`plugin marketplace list`, `plugin
list`): o operador que rodou a mao os comandos de `claude_cli_ausente` nao trava o
integrate seguinte num `add` repetido, e um detach interrompido no meio nao tenta de
novo o `uninstall` do que ja saiu. Lista que falha ou nao se le nao pula o passo.

A versao do plugin e `<versao do pacote>+<8 hex>` do conteudo (skills, agents e
`.mcp.json`): trocar o Python ou o bundle muda a versao, e o `plugin update` do Claude
a enxerga.

Sem `claude` no PATH o diretorio fica montado e sai a recusa `claude_cli_ausente`
com os comandos que o operador roda. O executor e injetavel (`runner`, `which`):
nenhum teste chama o binario de verdade.

No dry-run o `which` e consultado do mesmo jeito: o ensaio diz a mesma recusa que
a execucao diria, e so nao chama o CLI.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.integrate.hosts import (
    MARKETPLACE,
    PLUGIN,
    claude_marketplace_dir,
    claude_plugin_dir,
    mcp_command,
)

Runner = Callable[[list[str]], tuple[int, str]]
Which = Callable[[str], str | None]

DESCRICAO = (
    "Analise deterministica de jobs PySpark no AWS Glue e no Amazon EMR: facts por AST "
    "e dumps coletados, julgamento contra catalogo de regras versionado, e case que "
    "atravessa sessoes."
)
PLUGIN_ID = f"{PLUGIN}@{MARKETPLACE}"
# Segundos que um comando do `claude` pode levar antes de virar `claude_cli_timeout`.
TIMEOUT_S = 120
SAIDA_MAX = 400


def _json(dados: dict[str, Any]) -> bytes:
    return (json.dumps(dados, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def content_version(version: str, arquivos: Iterable[tuple[Path, bytes]], base: Path) -> str:
    """`<version>+<8 hex>`: o sha256 dos caminhos (relativos a `base`) e bytes."""
    soma = hashlib.sha256()
    for caminho, dados in sorted((Path(c).relative_to(base).as_posix(), d) for c, d in arquivos):
        soma.update(caminho.encode("utf-8") + b"\0")
        soma.update(hashlib.sha256(dados).digest())
    return f"{version}+{soma.hexdigest()[:8]}"


def plugin_files(
    home: Path,
    *,
    version: str,
    python: str | None,
    content: Iterable[tuple[Path, bytes]] = (),
) -> list[tuple[Path, bytes]]:
    """Os tres arquivos do marketplace e do plugin que nao sao skill nem agent.

    `content` sao as skills e os agents do plugin: entram, com o `.mcp.json`, no
    sha que vai na versao."""
    marketplace = claude_marketplace_dir(home)
    plugin = claude_plugin_dir(home)
    comando, args = mcp_command(python)
    # O Python que TEM o sparkforge instalado, sem PYTHONPATH para repositorio nenhum.
    mcp = _json({"mcpServers": {"sparkforge": {"command": comando, "args": args}}})
    versao = content_version(version, [*content, (plugin / ".mcp.json", mcp)], plugin)
    catalogo = {
        "name": MARKETPLACE,
        "owner": {"name": "SparkForge AWS"},
        "plugins": [
            {
                "name": PLUGIN,
                "source": f"./plugins/{PLUGIN}",
                "description": DESCRICAO,
                "version": versao,
            }
        ],
    }
    manifesto = {
        "name": PLUGIN,
        "version": versao,
        "description": DESCRICAO,
        "author": {"name": "SparkForge AWS"},
        "license": "MIT",
    }
    return [
        (marketplace / ".claude-plugin" / "marketplace.json", _json(catalogo)),
        (plugin / ".claude-plugin" / "plugin.json", _json(manifesto)),
        (plugin / ".mcp.json", mcp),
    ]


# --------------------------------------------------------------------------
# Os passos do CLI
# --------------------------------------------------------------------------

LISTA_MARKETPLACES = ["plugin", "marketplace", "list", "--json"]
LISTA_PLUGINS = ["plugin", "list", "--json"]


def _menciona(dados: Any, alvo: str) -> bool:
    """`alvo` aparece como chave ou valor em algum ponto do JSON."""
    if isinstance(dados, str):
        return dados == alvo
    if isinstance(dados, dict):
        return any(_menciona(k, alvo) or _menciona(v, alvo) for k, v in dados.items())
    if isinstance(dados, list):
        return any(_menciona(item, alvo) for item in dados)
    return False


def _tem_plugin(dados: Any) -> bool:
    """O plugin, por id (`nome@marketplace`) ou por nome e marketplace separados."""
    if _menciona(dados, PLUGIN_ID):
        return True
    if isinstance(dados, dict):
        valores = set(v for v in dados.values() if isinstance(v, str))
        if {PLUGIN, MARKETPLACE} <= valores:
            return True
        return any(_tem_plugin(v) for v in dados.values())
    if isinstance(dados, list):
        return any(_tem_plugin(item) for item in dados)
    return False


def _tem_marketplace(dados: Any) -> bool:
    return _menciona(dados, MARKETPLACE)


@dataclass(frozen=True)
class Passo:
    """Um comando do `claude`, com a conferencia que o torna desnecessario.

    `pular_se_presente=True` (add, install): pula quando a lista ja o mostra.
    `False` (uninstall, remove): pula quando a lista nao o mostra mais."""

    argv: list[str]
    lista: list[str] | None = None
    presente: Callable[[Any], bool] | None = None
    pular_se_presente: bool = True


def register_steps(home: Path, *, primeira: bool) -> list[Passo]:
    """Registrar (primeira vez) ou atualizar."""
    if primeira:
        return [
            Passo(["plugin", "marketplace", "add", str(claude_marketplace_dir(home)),
                   "--scope", "user"], LISTA_MARKETPLACES, _tem_marketplace),
            Passo(["plugin", "install", PLUGIN_ID, "--scope", "user", "--json"],
                  LISTA_PLUGINS, _tem_plugin),
        ]
    return [
        Passo(["plugin", "marketplace", "update", MARKETPLACE]),
        Passo(["plugin", "update", PLUGIN_ID]),
    ]


def register_commands(home: Path, *, primeira: bool) -> list[list[str]]:
    """Os argumentos do `claude` (sem o executavel): registrar, ou atualizar."""
    return [passo.argv for passo in register_steps(home, primeira=primeira)]


def unregister_steps() -> list[Passo]:
    return [
        Passo(["plugin", "uninstall", PLUGIN_ID, "--scope", "user"],
              LISTA_PLUGINS, _tem_plugin, pular_se_presente=False),
        Passo(["plugin", "marketplace", "remove", MARKETPLACE, "--scope", "user"],
              LISTA_MARKETPLACES, _tem_marketplace, pular_se_presente=False),
    ]


def unregister_commands() -> list[list[str]]:
    return [passo.argv for passo in unregister_steps()]


def _linha(argv: list[str]) -> str:
    """O comando como o operador o cola no proprio shell, com aspas onde precisa."""
    completo = ["claude", *argv]
    if os.name == "nt":
        return subprocess.list2cmdline(completo)
    return shlex.join(completo)


def _mostrar(comandos: list[list[str]]) -> list[str]:
    return [_linha(argv) for argv in comandos]


def run(argv: list[str]) -> tuple[int, str]:
    """O executor de verdade. `argv[0]` e o caminho absoluto que `which` achou.

    `stdin` fechado e `TIMEOUT_S`: um prompt sem TTY falha em vez de esperar.
    `TimeoutExpired` e `OSError` sobem; `_executar` os troca por recusa nomeada."""
    proc = subprocess.run(  # noqa: S603
        argv,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_S,
        check=False,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# Os executores de producao, lidos na hora da chamada: o teste os troca aqui, e
# nenhum caminho sem `runner`/`which` injetados chega ao binario de verdade.
RUNNER_PADRAO: Runner = run
WHICH_PADRAO: Which = shutil.which


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bytes):
        return valor.decode("utf-8", errors="replace")
    return str(valor)


def _chamar(
    executavel: str, argv: list[str], runner: Runner
) -> tuple[int, str] | dict[str, Any]:
    """Roda um comando; excecao do executor vira a recusa nomeada."""
    try:
        return runner([executavel, *argv])
    except subprocess.TimeoutExpired as erro:
        saida = _texto(erro.stdout) + _texto(erro.stderr)
        return {
            "status": "refused",
            "reason": "claude_cli_timeout",
            "command": _linha(argv),
            "timeout_s": erro.timeout,
            "output": saida[-SAIDA_MAX:],
        }
    except OSError as erro:
        return {
            "status": "refused",
            "reason": "claude_cli_falhou",
            "command": _linha(argv),
            "output": str(erro)[-SAIDA_MAX:],
        }


def _json_da_saida(saida: str) -> Any:
    """O JSON da saida do `list --json`; `None` quando nao se le."""
    decodificador = json.JSONDecoder()
    for inicio in sorted(i for i in (saida.find("["), saida.find("{")) if i >= 0):
        try:
            return decodificador.raw_decode(saida[inicio:])[0]
        except ValueError:
            continue
    return None


def _desnecessario(executavel: str, passo: Passo, runner: Runner) -> bool | dict[str, Any]:
    """O passo ja esta feito, pela lista? Lista que falha ou nao se le: nao."""
    if passo.lista is None or passo.presente is None:
        return False
    listado = _chamar(executavel, passo.lista, runner)
    if isinstance(listado, dict):
        return listado
    codigo, saida = listado
    dados = _json_da_saida(saida) if codigo == 0 else None
    if dados is None:
        return False
    return passo.presente(dados) == passo.pular_se_presente


def _executar(
    passos: list[Passo],
    *,
    dry_run: bool,
    runner: Runner | None,
    which: Which | None,
) -> dict[str, Any]:
    comandos = [passo.argv for passo in passos]
    executavel = (which or WHICH_PADRAO)("claude")
    if executavel is None:
        return {
            "status": "refused",
            "reason": "claude_cli_ausente",
            "commands": _mostrar(comandos),
        }
    if dry_run:
        return {"status": "dry_run", "commands": _mostrar(comandos)}
    executor = runner or RUNNER_PADRAO
    feitos: list[list[str]] = []
    pulados: list[list[str]] = []
    for passo in passos:
        pular = _desnecessario(executavel, passo, executor)
        if isinstance(pular, dict):
            return pular
        if pular:
            pulados.append(passo.argv)
            continue
        resultado = _chamar(executavel, passo.argv, executor)
        if isinstance(resultado, dict):
            return resultado
        codigo, saida = resultado
        if codigo != 0:
            return {
                "status": "refused",
                "reason": "claude_cli_falhou",
                "command": _linha(passo.argv),
                "output": saida[-SAIDA_MAX:],
            }
        feitos.append(passo.argv)
    return {"status": "ok", "commands": _mostrar(feitos), "skipped": _mostrar(pulados)}


def register(
    home: Path,
    *,
    primeira: bool,
    mudou: bool,
    dry_run: bool,
    runner: Runner | None = None,
    which: Which | None = None,
) -> dict[str, Any]:
    """Registra (ou atualiza) o plugin no Claude Code pelo CLI dele."""
    if not primeira and not mudou:
        return {"status": "unchanged", "commands": []}
    passos = register_steps(home, primeira=primeira)
    return _executar(passos, dry_run=dry_run, runner=runner, which=which)


def unregister(
    *, dry_run: bool, runner: Runner | None = None, which: Which | None = None
) -> dict[str, Any]:
    return _executar(unregister_steps(), dry_run=dry_run, runner=runner, which=which)


__all__ = [
    "DESCRICAO",
    "PLUGIN_ID",
    "RUNNER_PADRAO",
    "TIMEOUT_S",
    "WHICH_PADRAO",
    "Passo",
    "content_version",
    "plugin_files",
    "register",
    "register_commands",
    "register_steps",
    "run",
    "unregister",
    "unregister_commands",
    "unregister_steps",
]
