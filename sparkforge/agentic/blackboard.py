"""Shared Blackboard — estado estruturado do case em árvore de arquivos.

Evolui de `case.yaml` único para uma árvore estruturada sob `.sparkforge/`:

```
.sparkforge/
  case.yaml           # metadata + phase + gates (existente, preservado)
  blackboard/
    claims.jsonl      # claims feitas por agentes
    hypotheses.jsonl  # hipóteses geradas
    objections.jsonl  # objeções levantadas
    contradictions.jsonl
    evidence.jsonl    # evidência classificada
    experiments.jsonl
    decisions.jsonl
    unknowns.jsonl
    traces.jsonl      # trace events
```

Cada arquivo é append-only JSONL. Agentes leem apenas o que precisam,
não o transcript completo. O `case.yaml` existente continua válido e
não é modificado — o blackboard é uma camada adicional.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.agentic.models import (
    Claim,
    Contradiction,
    Decision,
    Evidence,
    Experiment,
    Hypothesis,
    Objection,
    Rebuttal,
    Unknown,
)
from sparkforge.case.store import CASE_DIR

BLACKBOARD_DIR = "blackboard"

# Mapeamento: tipo de entidade -> nome do arquivo JSONL
_ENTITY_FILES: dict[str, str] = {
    "claim": "claims.jsonl",
    "evidence": "evidence.jsonl",
    "hypothesis": "hypotheses.jsonl",
    "objection": "objections.jsonl",
    "rebuttal": "rebuttals.jsonl",
    "contradiction": "contradictions.jsonl",
    "experiment": "experiments.jsonl",
    "decision": "decisions.jsonl",
    "unknown": "unknowns.jsonl",
    "trace": "traces.jsonl",
}


def blackboard_path(root: Path | str) -> Path:
    """Retorna o path do diretório blackboard."""
    return Path(root) / CASE_DIR / BLACKBOARD_DIR


def init_blackboard(root: Path | str) -> Path:
    """Cria a estrutura de diretório do blackboard se não existir.

    Não cria arquivos vazios — eles são criados on-demand no append.
    """
    bb_dir = blackboard_path(root)
    bb_dir.mkdir(parents=True, exist_ok=True)
    return bb_dir


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append um registro JSONL. Cria o arquivo se não existir."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=True, sort_keys=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Lê todos os registros de um arquivo JSONL."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _entity_file(root: Path | str, entity_type: str) -> Path:
    """Retorna o path do arquivo JSONL para um tipo de entidade."""
    filename = _ENTITY_FILES.get(entity_type)
    if not filename:
        raise ValueError(
            f"Tipo de entidade desconhecido: {entity_type!r}. "
            f"Esperado: {', '.join(sorted(_ENTITY_FILES))}"
        )
    return blackboard_path(root) / filename


# ======================================================================
# Append operations — uma por tipo de entidade
# ======================================================================


def append_claim(claim: Claim, root: Path | str) -> Path:
    _validate_no_duplicate(claim.id, root, "claim")
    _append_jsonl(_entity_file(root, "claim"), claim.to_dict())
    return _entity_file(root, "claim")


def append_evidence(evidence: Evidence, root: Path | str) -> Path:
    _validate_no_duplicate(evidence.id, root, "evidence")
    _append_jsonl(_entity_file(root, "evidence"), evidence.to_dict())
    return _entity_file(root, "evidence")


def append_hypothesis(hypothesis: Hypothesis, root: Path | str) -> Path:
    _validate_no_duplicate(hypothesis.id, root, "hypothesis")
    _append_jsonl(_entity_file(root, "hypothesis"), hypothesis.to_dict())
    return _entity_file(root, "hypothesis")


def append_objection(objection: Objection, root: Path | str) -> Path:
    _validate_no_duplicate(objection.id, root, "objection")
    _append_jsonl(_entity_file(root, "objection"), objection.to_dict())
    return _entity_file(root, "objection")


def append_rebuttal(rebuttal: Rebuttal, root: Path | str) -> Path:
    _validate_no_duplicate(rebuttal.id, root, "rebuttal")
    _append_jsonl(_entity_file(root, "rebuttal"), rebuttal.to_dict())
    return _entity_file(root, "rebuttal")


def append_contradiction(contradiction: Contradiction, root: Path | str) -> Path:
    _validate_no_duplicate(contradiction.id, root, "contradiction")
    _append_jsonl(_entity_file(root, "contradiction"), contradiction.to_dict())
    return _entity_file(root, "contradiction")


def append_experiment(experiment: Experiment, root: Path | str) -> Path:
    _validate_no_duplicate(experiment.id, root, "experiment")
    _append_jsonl(_entity_file(root, "experiment"), experiment.to_dict())
    return _entity_file(root, "experiment")


def append_decision(decision: Decision, root: Path | str) -> Path:
    _validate_no_duplicate(decision.id, root, "decision")
    _append_jsonl(_entity_file(root, "decision"), decision.to_dict())
    return _entity_file(root, "decision")


def append_unknown(unknown: Unknown, root: Path | str) -> Path:
    _validate_no_duplicate(unknown.id, root, "unknown")
    _append_jsonl(_entity_file(root, "unknown"), unknown.to_dict())
    return _entity_file(root, "unknown")


def append_trace(trace: dict[str, Any], root: Path | str) -> Path:
    """Append um trace event genérico (sem dedup — traces são append-only)."""
    if "id" not in trace:
        raise ValueError("trace deve ter 'id'")
    _append_jsonl(_entity_file(root, "trace"), trace)
    return _entity_file(root, "trace")


# ======================================================================
# Read operations — uma por tipo de entidade
# ======================================================================


def read_claims(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "claim"))


def read_evidence(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "evidence"))


def read_hypotheses(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "hypothesis"))


def read_objections(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "objection"))


def read_rebuttals(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "rebuttal"))


def read_contradictions(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "contradiction"))


def read_experiments(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "experiment"))


def read_decisions(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "decision"))


def read_unknowns(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "unknown"))


def read_traces(root: Path | str) -> list[dict[str, Any]]:
    return _read_jsonl(_entity_file(root, "trace"))


# ======================================================================
# Query operations
# ======================================================================


@dataclass
class BlackboardSummary:
    """Resumo do estado do blackboard para quick inspection."""

    claims: int
    evidence: int
    hypotheses: int
    objections: int
    rebuttals: int
    contradictions: int
    experiments: int
    decisions: int
    unknowns: int
    open_unknowns: int
    open_hypotheses: int
    unresolved_contradictions: int


def summarize(root: Path | str) -> BlackboardSummary:
    """Retorna um resumo contável do blackboard."""
    claims = read_claims(root)
    evidence = read_evidence(root)
    hypotheses = read_hypotheses(root)
    objections = read_objections(root)
    rebuttals = read_rebuttals(root)
    contradictions = read_contradictions(root)
    experiments = read_experiments(root)
    decisions = read_decisions(root)
    unknowns = read_unknowns(root)

    open_unknowns = sum(1 for u in unknowns if u.get("status") == "open")
    open_hypotheses = sum(1 for h in hypotheses if h.get("status") == "open")
    unresolved_contradictions = sum(
        1 for c in contradictions if c.get("resolution") in (None, "unresolved")
    )

    return BlackboardSummary(
        claims=len(claims),
        evidence=len(evidence),
        hypotheses=len(hypotheses),
        objections=len(objections),
        rebuttals=len(rebuttals),
        contradictions=len(contradictions),
        experiments=len(experiments),
        decisions=len(decisions),
        unknowns=len(unknowns),
        open_unknowns=open_unknowns,
        open_hypotheses=open_hypotheses,
        unresolved_contradictions=unresolved_contradictions,
    )


def get_entity_by_id(entity_id: str, root: Path | str) -> dict[str, Any] | None:
    """Busca uma entidade por id em todos os arquivos do blackboard.

    Retorna o primeiro match ou None. O id é único por tipo (content-addressed),
    mas pode haver ids colisionando entre tipos (prefixos diferentes mitigam).
    """
    readers = [
        read_claims,
        read_evidence,
        read_hypotheses,
        read_objections,
        read_rebuttals,
        read_contradictions,
        read_experiments,
        read_decisions,
        read_unknowns,
    ]
    for reader in readers:
        for record in reader(root):
            if record.get("id") == entity_id:
                return record
    return None


# ======================================================================
# Internals
# ======================================================================


def _validate_no_duplicate(entity_id: str, root: Path | str, entity_type: str) -> None:
    """Verifica que o id não existe já no blackboard.

    Append-only com dedup: o mesmo id twice significa que o caller está
    re-adicionando a mesma entidade, o que é um bug (use update se preciso).
    Exceção: traces não passam por aqui (append puro).
    """
    existing = _read_jsonl(_entity_file(root, entity_type))
    for record in existing:
        if record.get("id") == entity_id:
            raise ValueError(
                f"Entidade {entity_type} com id {entity_id!r} já existe no blackboard. "
                f"Append-only: use update explícito se precisa modificar."
            )
