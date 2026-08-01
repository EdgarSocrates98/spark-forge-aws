"""Decomposicao de um coordenador em passos sequenciais.

Existe porque despacho de subagente e capacidade de HARNESS, nao conteudo deste
repositorio: Devin, Codex e Copilot nao tem equivalente. O playbook emite a
mesma decomposicao em ordem, para um agente so seguir.

Le os arquivos de `agents/` em vez de repetir a lista de executores: uma copia
aqui divergiria do coordenador na primeira mudanca, e o espelho viraria prosa
que envelhece -- o motivo de a decisao F4-D4 ter escolhido verbo em vez de
documento.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "agents"
EXECUTORS = AGENTS / "executors"


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name} sem frontmatter")
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def _section(text: str, title: str) -> str:
    """Corpo de uma secao `## <title>` ate a proxima `##` ou o fim."""
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""


def available_coordinators() -> list[str]:
    return sorted(p.stem for p in AGENTS.glob("*.md"))


def build_playbook(coordinator: str, case: dict[str, Any]) -> dict[str, Any]:
    """Passos ordenados de um coordenador, com o estado do case.

    `does_not` vem da secao `## Não faz` do executor -- nao e reescrito aqui.
    Duas fontes para a mesma fronteira divergiriam, e a que ninguem le seria a
    errada.
    """
    path = AGENTS / f"{coordinator}.md"
    if not path.is_file():
        raise ValueError(
            f"coordenador desconhecido: {coordinator}. Rode `sparkforge playbook "
            f"<coordenador>` com um dos disponiveis: {', '.join(available_coordinators())}"
        )

    front = _frontmatter(path)
    steps: list[dict[str, Any]] = []
    for order, name in enumerate(front.get("executors") or [], start=1):
        executor_path = EXECUTORS / f"{name}.md"
        if not executor_path.is_file():
            raise ValueError(
                f"{coordinator} declara o executor {name}, que nao existe em "
                f"{EXECUTORS.relative_to(ROOT)}"
            )
        text = executor_path.read_text(encoding="utf-8")
        steps.append(
            {
                "order": order,
                "executor": name,
                "function": _frontmatter(executor_path).get("function", ""),
                "does": _section(text, "Faz"),
                "does_not": _section(text, "Não faz"),
            }
        )

    return {
        "coordinator": coordinator,
        "description": front.get("description", ""),
        "rule_areas": front.get("rule_areas") or [],
        "skills": front.get("skills") or [],
        "phase": case.get("phase"),
        "steps": steps,
        "note": (
            "Decomposicao sequencial. Em Claude Code os mesmos passos sao "
            "despachados como subagentes; aqui um agente so os segue em ordem, "
            "escrevendo o resultado de cada um no case antes do proximo."
        ),
    }
