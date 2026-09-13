"""`permissions.ask` do `.claude/settings.json`, gerado da policy.

A lista `permissions.ask` passa a ser DONA da policy: `sync-settings` a
substitui inteira, e o resto do arquivo fica como estava. Regras `ask` do
Claude Code sao avaliadas deny -> ask -> allow e pedem confirmacao ate em modo
auto (documentacao de permissoes, 2026-09-13).
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sparkforge.policy.decide import ASK
from sparkforge.policy.load import Politica

SETTINGS_RELATIVE = Path(".claude") / "settings.json"
SERVIDOR_MCP = "sparkforge"


def regras_ask(politica: Politica, tools_por_classe: Mapping[str, Sequence[str]]) -> list[str]:
    regras: list[str] = []
    for regra in politica.bash:
        if regra.decision == ASK:
            regras.append(f"Bash({regra.rule})")
    for regra in politica.paths:
        if regra.decision == ASK:
            regras += [f"Edit({regra.rule})", f"Write({regra.rule})"]
    nomes = set(politica.ask_names)
    for classe in politica.ask_classes:
        nomes |= set(tools_por_classe.get(classe, ()))
    nomes -= set(politica.denied)
    regras += [f"mcp__{SERVIDOR_MCP}__{nome}" for nome in sorted(nomes)]
    return list(dict.fromkeys(regras))


def sincronizar(
    raiz: Path | str,
    politica: Politica,
    tools_por_classe: Mapping[str, Sequence[str]],
    check: bool = False,
) -> dict[str, Any]:
    alvo = Path(raiz) / SETTINGS_RELATIVE
    dados: dict[str, Any] = (
        json.loads(alvo.read_text(encoding="utf-8")) if alvo.is_file() else {}
    )
    esperado = regras_ask(politica, tools_por_classe)
    atual = (dados.get("permissions") or {}).get("ask")
    em_dia = atual == esperado
    gravou = False
    if not check and not em_dia:
        dados.setdefault("permissions", {})["ask"] = esperado
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
        gravou = True
    return {
        "settings": SETTINGS_RELATIVE.as_posix(),
        "ask": esperado,
        "in_sync": em_dia,
        "written": gravou,
    }
