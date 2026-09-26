"""Claude Code: o plugin por marketplace local (D8).

Monta em `~/.sparkforge/claude/` o marketplace `sparkforge-local`, com o plugin
`sparkforge-aws` em `plugins/sparkforge-aws/` (skills, agents, `.mcp.json` e
`.claude-plugin/plugin.json`), e o registra pelo proprio CLI do Claude:

    claude plugin marketplace add <dir> --scope user
    claude plugin install sparkforge-aws@sparkforge-local --scope user --json

Os flags foram conferidos no `--help` do Claude Code 2.1.283. `~/.claude/settings.json`
nao e editado a mao: e formato interno do Claude, e muda sem aviso.

Sem `claude` no PATH o diretorio fica montado e sai a recusa `claude_cli_ausente`
com os comandos que o operador roda. O executor e injetavel (`runner`, `which`):
nenhum teste chama o binario de verdade.

No dry-run o `which` e consultado do mesmo jeito: o ensaio diz a mesma recusa que
a execucao diria, e so nao chama o CLI.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
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


def _json(dados: dict[str, Any]) -> bytes:
    return (json.dumps(dados, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def plugin_files(home: Path, *, version: str, python: str | None) -> list[tuple[Path, bytes]]:
    """Os tres arquivos do marketplace e do plugin que nao sao skill nem agent."""
    marketplace = claude_marketplace_dir(home)
    plugin = claude_plugin_dir(home)
    comando, args = mcp_command(python)
    catalogo = {
        "name": MARKETPLACE,
        "owner": {"name": "SparkForge AWS"},
        "plugins": [
            {
                "name": PLUGIN,
                "source": f"./plugins/{PLUGIN}",
                "description": DESCRICAO,
                "version": version,
            }
        ],
    }
    manifesto = {
        "name": PLUGIN,
        "version": version,
        "description": DESCRICAO,
        "author": {"name": "SparkForge AWS"},
        "license": "MIT",
    }
    # O Python que TEM o sparkforge instalado, sem PYTHONPATH para repositorio nenhum.
    mcp = {"mcpServers": {"sparkforge": {"command": comando, "args": args}}}
    return [
        (marketplace / ".claude-plugin" / "marketplace.json", _json(catalogo)),
        (plugin / ".claude-plugin" / "plugin.json", _json(manifesto)),
        (plugin / ".mcp.json", _json(mcp)),
    ]


def register_commands(home: Path, *, primeira: bool) -> list[list[str]]:
    """Os argumentos do `claude` (sem o executavel): registrar, ou atualizar."""
    if primeira:
        return [
            ["plugin", "marketplace", "add", str(claude_marketplace_dir(home)),
             "--scope", "user"],
            ["plugin", "install", PLUGIN_ID, "--scope", "user", "--json"],
        ]
    return [
        ["plugin", "marketplace", "update", MARKETPLACE],
        ["plugin", "update", PLUGIN_ID],
    ]


def unregister_commands() -> list[list[str]]:
    return [
        ["plugin", "uninstall", PLUGIN_ID, "--scope", "user"],
        ["plugin", "marketplace", "remove", MARKETPLACE, "--scope", "user"],
    ]


def _mostrar(comandos: list[list[str]]) -> list[str]:
    return [" ".join(["claude", *argv]) for argv in comandos]


def run(argv: list[str]) -> tuple[int, str]:
    """O executor de verdade. `argv[0]` e o caminho absoluto que `which` achou."""
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# Os executores de producao, lidos na hora da chamada: o teste os troca aqui, e
# nenhum caminho sem `runner`/`which` injetados chega ao binario de verdade.
RUNNER_PADRAO: Runner = run
WHICH_PADRAO: Which = shutil.which


def _executar(
    comandos: list[list[str]],
    *,
    dry_run: bool,
    runner: Runner | None,
    which: Which | None,
) -> dict[str, Any]:
    executavel = (which or WHICH_PADRAO)("claude")
    if executavel is None:
        return {
            "status": "refused",
            "reason": "claude_cli_ausente",
            "commands": _mostrar(comandos),
        }
    if dry_run:
        return {"status": "dry_run", "commands": _mostrar(comandos)}
    for argv in comandos:
        codigo, saida = (runner or RUNNER_PADRAO)([executavel, *argv])
        if codigo != 0:
            return {
                "status": "refused",
                "reason": "claude_cli_falhou",
                "command": _mostrar([argv])[0],
                "output": saida[-400:],
            }
    return {"status": "ok", "commands": _mostrar(comandos)}


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
    comandos = register_commands(home, primeira=primeira)
    return _executar(comandos, dry_run=dry_run, runner=runner, which=which)


def unregister(
    *, dry_run: bool, runner: Runner | None = None, which: Which | None = None
) -> dict[str, Any]:
    return _executar(unregister_commands(), dry_run=dry_run, runner=runner, which=which)


__all__ = [
    "DESCRICAO",
    "PLUGIN_ID",
    "RUNNER_PADRAO",
    "WHICH_PADRAO",
    "plugin_files",
    "register",
    "register_commands",
    "run",
    "unregister",
    "unregister_commands",
]
