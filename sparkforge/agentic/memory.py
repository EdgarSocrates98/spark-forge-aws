"""Decision Memory — memória de decisões跨-case.

Três níveis de memória:
1. Working memory — contexto da sessão atual (não persiste)
2. Case memory — decisões dentro de um case (persiste no blackboard)
3. Institutional memory — decisões跨-case, "what worked in similar problems"

Institutional memory é um índice de decisões passadas que pode ser consultado
para evitar repetir erros e reusar soluções provadas. É armazenado em
`.sparkforge/memory/decisions.jsonl` no root do repositório.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkforge.agentic.models import Decision
from sparkforge.case.store import CASE_DIR

MEMORY_DIR = "memory"
DECISIONS_FILE = "decisions.jsonl"


def memory_path(root: Path | str) -> Path:
    """Retorna o path do diretório de memória institucional."""
    return Path(root) / CASE_DIR / MEMORY_DIR


def decisions_file_path(root: Path | str) -> Path:
    """Retorna o path do arquivo de decisões institucionais."""
    return memory_path(root) / DECISIONS_FILE


def init_memory(root: Path | str) -> Path:
    """Cria a estrutura de diretório de memória se não existir."""
    p = memory_path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def record_decision(decision: Decision, root: Path | str, case_id: str = "") -> Path:
    """Registra uma decisão na memória institucional.

    A decisão é armazenada com:
    - decision data
    - case_id (para rastreabilidade)
    - outcome (inicialmente empty — updated later)
    """
    init_memory(root)
    record = decision.to_dict()
    record["case_id"] = case_id
    record["outcome"] = ""  # updated by update_outcome
    record["outcome_evidence"] = []

    path = decisions_file_path(root)
    # Check for duplicate
    existing = _read_decisions(root)
    for e in existing:
        if e.get("id") == decision.id:
            raise ValueError(
                f"Decision {decision.id!r} já existe na memória institucional."
            )

    line = json.dumps(record, ensure_ascii=True, sort_keys=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return path


def update_outcome(
    decision_id: str,
    outcome: str,
    root: Path | str,
    evidence: list[str] | None = None,
) -> None:
    """Atualiza o outcome de uma decisão registrada.

    Outcome descreve se a decisão funcionou, falhou, ou foi revertida.
    Isso é o "learning" que alimenta decisões futuras.
    """
    decisions = _read_decisions(root)
    updated = False
    for d in decisions:
        if d.get("id") == decision_id:
            d["outcome"] = outcome
            d["outcome_evidence"] = evidence or []
            updated = True
            break

    if not updated:
        raise ValueError(
            f"Decision {decision_id!r} não encontrada na memória institucional."
        )

    # Rewrite file
    path = decisions_file_path(root)
    with path.open("w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=True, sort_keys=True) + "\n")


def _read_decisions(root: Path | str) -> list[dict[str, Any]]:
    """Lê todas as decisões da memória institucional."""
    path = decisions_file_path(root)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def find_similar_decisions(
    problem: str,
    root: Path | str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Encontra decisões passadas com problema similar.

    Heurística simples: matching de keywords no problem.
    Retorna decisões ordenadas por relevância (keyword overlap).
    """
    decisions = _read_decisions(root)
    if not decisions:
        return []

    problem_words = set(problem.lower().split())
    scored: list[tuple[float, dict[str, Any]]] = []
    for d in decisions:
        d_problem = d.get("problem", "").lower()
        d_words = set(d_problem.split())
        overlap = len(problem_words & d_words)
        if overlap > 0:
            # Boost decisions with positive outcomes
            outcome = d.get("outcome", "").lower()
            boost = 1.5 if "success" in outcome or "worked" in outcome else 1.0
            scored.append((overlap * boost, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:limit]]


def get_decision_history(root: Path | str) -> list[dict[str, Any]]:
    """Retorna todas as decisões registradas, em ordem cronológica."""
    return _read_decisions(root)


@dataclass
class MemoryStats:
    """Estatísticas da memória institucional."""

    total_decisions: int
    decisions_with_outcome: int
    successful_outcomes: int
    failed_outcomes: int
    reverted_outcomes: int
    unique_problems: int


def memory_stats(root: Path | str) -> MemoryStats:
    """Computa estatísticas da memória institucional."""
    decisions = _read_decisions(root)
    total = len(decisions)
    with_outcome = sum(1 for d in decisions if d.get("outcome"))
    successful = sum(1 for d in decisions if "success" in d.get("outcome", "").lower() or "worked" in d.get("outcome", "").lower())
    failed = sum(1 for d in decisions if "fail" in d.get("outcome", "").lower())
    reverted = sum(1 for d in decisions if "revert" in d.get("outcome", "").lower())
    problems = {d.get("problem", "") for d in decisions}

    return MemoryStats(
        total_decisions=total,
        decisions_with_outcome=with_outcome,
        successful_outcomes=successful,
        failed_outcomes=failed,
        reverted_outcomes=reverted,
        unique_problems=len(problems),
    )
