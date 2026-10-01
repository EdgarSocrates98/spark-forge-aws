"""A policy como `CallPolicy` do servidor MCP.

Importa o catalogo de tools: roda UMA vez, quando o servidor sobe -- nunca no
caminho do hook.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.policy.load import Politica


def raizes(politica: Politica, raiz: Path | str) -> tuple[Path, ...]:
    base = Path(raiz)
    extras = tuple(Path(r) if Path(r).is_absolute() else base / r for r in politica.extra_roots)
    return (base, *extras)


def tools_por_classe() -> dict[str, list[str]]:
    from sparkforge.adapters.tools import TOOLS
    from sparkforge.agents.autonomy import tool_class

    grupos: dict[str, list[str]] = {}
    for nome in sorted(TOOLS):
        grupos.setdefault(tool_class(nome).name, []).append(nome)
    return grupos


def para_call_policy(politica: Politica, raiz: Path | str) -> Any:
    """Allowlist = catalogo inteiro; a policy so RECUSA (`denied`), declara as
    classes pre-aprovadas e as raizes. Perfil `balanced`: o de hoje."""
    from sparkforge.adapters.tools import TOOLS
    from sparkforge.agents.autonomy import CallPolicy, ToolClass
    from sparkforge.registry.models import ExecutionProfile

    return CallPolicy(
        agent="policy.yaml",
        allowed_tools=tuple(sorted(TOOLS)),
        profile=ExecutionProfile.BALANCED,
        root=raizes(politica, raiz),
        approvals=tuple(ToolClass[c] for c in politica.approvals),
        denied_tools=politica.denied,
    )
