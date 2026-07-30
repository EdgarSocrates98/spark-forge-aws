"""Leitura e escrita de `.sparkforge/case.yaml` — o barramento de handoff.

O case file é o que atravessa a fronteira entre uma sessão Devin e uma sessão
Claude Code: são processos diferentes, sem contexto conversacional compartilhado.
O que sobrevive é um commit, e o case file é o estado desse commit.

Timestamp nunca é gerado aqui. Todo `created_at`/`at` chega como parâmetro,
injetado por quem chama (o adapter de CLI, tipicamente `datetime.now(UTC)`).
Isto mantém o módulo puro e reprodutível, e impede um LLM de inventar hora.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1
CASE_DIR = ".sparkforge"
CASE_FILE = "case.yaml"

PHASES = (
    "intake",
    "inventory",
    "facts",
    "diagnosis",
    "hypothesis",
    "experiment",
    "validation",
    "report",
)

GATES = (
    "baseline_captured",
    "dominant_bottleneck_identified",
    "functional_validation_defined",
    "flows_mapped",
)


class CaseError(ValueError):
    """Case ausente, malformado, ou mutação com valor fora do domínio."""


def case_path(root: Path | str) -> Path:
    return Path(root) / CASE_DIR / CASE_FILE


def new_case(
    case_id: str,
    created_at: str,
    runtime: dict[str, Any],
    repo: str = "",
) -> dict[str, Any]:
    """Cria um case novo em fase `intake`, todos os gates falsos.

    `created_at` é injetado, nunca gerado: ver nota do módulo.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "created_at": created_at,
        "runtime": copy.deepcopy(runtime),
        "scope": {
            "repo": repo,
            "entrypoints": [],
            "job_names": [],
            "consumers": [],
        },
        "phase": "intake",
        "artifacts": [],
        "facts_index": {"path": "", "count": 0, "by_kind": {}},
        "findings_index": {"path": "", "count": 0, "by_severity": {}},
        "baseline": None,
        "hypotheses": [],
        "gates": dict.fromkeys(GATES, False),
        "skills_used": [],
        "open_questions": [],
    }


def save_case(case: dict[str, Any], root: Path | str) -> Path:
    """Escreve o case como YAML determinístico e legível em diff.

    Chaves ordenadas e `default_flow_style=False`: o mesmo case produz sempre o
    mesmo texto, condição necessária para o arquivo ser committável e revisável.
    """
    path = case_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        case, sort_keys=True, allow_unicode=True, default_flow_style=False
    )
    path.write_text(text, encoding="utf-8")
    return path


def load_case(root: Path | str) -> dict[str, Any]:
    """Carrega o case. Levanta CaseError se ausente ou schema divergente."""
    path = case_path(root)
    if not path.is_file():
        raise CaseError(
            f"Nenhum case em {path}. Rode `sparkforge case open` para criar um."
        )

    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise CaseError(f"{path}: YAML inválido: {exc}") from exc

    version = document.get("schema_version")
    if version != SCHEMA_VERSION:
        raise CaseError(
            f"{path}: schema_version {version!r} não suportado "
            f"(esperado {SCHEMA_VERSION})"
        )

    return document


def set_phase(case: dict[str, Any], phase: str) -> dict[str, Any]:
    if phase not in PHASES:
        raise CaseError(
            f"fase desconhecida: {phase!r} (esperado uma de: {', '.join(PHASES)})"
        )
    new = copy.deepcopy(case)
    new["phase"] = phase
    return new


def set_gate(case: dict[str, Any], gate: str, value: bool) -> dict[str, Any]:
    if gate not in GATES:
        raise CaseError(
            f"gate desconhecido: {gate!r} (esperado uma de: {', '.join(GATES)})"
        )
    new = copy.deepcopy(case)
    new["gates"][gate] = value
    return new


def add_hypothesis(
    case: dict[str, Any], statement: str, prediction: str, experiment: str
) -> dict[str, Any]:
    new = copy.deepcopy(case)
    hyp_id = f"h{len(new['hypotheses']) + 1}"
    new["hypotheses"].append(
        {
            "id": hyp_id,
            "statement": statement,
            "prediction": prediction,
            "experiment": experiment,
            "status": "open",
        }
    )
    return new


def record_skill_use(
    case: dict[str, Any], skill: str, at: str, outcome: str
) -> dict[str, Any]:
    new = copy.deepcopy(case)
    new["skills_used"].append({"skill": skill, "at": at, "outcome": outcome})
    return new


def set_index(
    case: dict[str, Any],
    which: str,
    path: str,
    count: int,
    breakdown: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Atualiza `facts_index` ou `findings_index` com contagem e detalhe."""
    if which == "facts_index":
        breakdown_key = "by_kind"
    elif which == "findings_index":
        breakdown_key = "by_severity"
    else:
        raise CaseError(
            f"índice desconhecido: {which!r} (esperado facts_index ou findings_index)"
        )
    new = copy.deepcopy(case)
    new[which] = {"path": path, "count": count, breakdown_key: dict(breakdown or {})}
    return new
