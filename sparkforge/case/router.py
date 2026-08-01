"""`next_step(case, finding_ids)` — roteamento determinístico sobre `routing.yaml`.

Mesma família de motor que `sparkforge.rules.engine`, mas o predicado é sobre o
estado do case (fase, gates, índices) e sobre a presença de achados, não sobre
facts extraídos. Puro: nunca chama LLM, nunca lê relógio, nunca escreve nada.

Predicado de roteamento é declarativo (ver `ROUTING_OPERATORS`), nunca
expressão livre — expressão exigiria `Call`/`In`, que a whitelist de
`sparkforge.rules.expr` proíbe, e o catálogo é dado editável, portanto
superfície de execução. Ver `rules/catalog/README.md`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sparkforge.rules.loader import (
    ROUTING_FILE,
    CatalogError,
    catalog_dir,
    safe_catalog_file,
)

ROUTING_OPERATORS = frozenset(
    {"equals", "absent", "present", "count_gt", "count_eq", "contains", "any_where"}
)

_MISSING = object()


def load_routing(directory: Path | None = None) -> dict[str, Any]:
    """Lê `routing.yaml`. Levanta CatalogError se ausente ou malformado."""
    base = directory or catalog_dir()
    path = safe_catalog_file(base, ROUTING_FILE)
    if not path.is_file():
        raise CatalogError(f"routing.yaml não encontrado em {path}")

    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    except yaml.YAMLError as exc:
        raise CatalogError(f"{path}: YAML inválido: {exc}") from exc

    if not isinstance(document.get("rules"), list):
        raise CatalogError(f"{path}: campo `rules` ausente ou não é lista")
    if not isinstance(document.get("fallback"), dict):
        raise CatalogError(f"{path}: campo `fallback` ausente ou não é mapa")

    return document


def _resolve_case_path(case: dict[str, Any], path: str) -> Any:
    value: Any = case
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return _MISSING
    return value


def _is_absent(value: Any) -> bool:
    return value is _MISSING or value is None or value in ([], {}, "")


def _count(value: Any) -> float | int | None:
    if isinstance(value, bool):
        # bool é subclasse de int em Python: True conta como 1, False como 0.
        # Nenhuma regra do catalogo hoje usa count_gt/count_eq sobre um gate
        # (todos usam `equals`), entao isto nao produz falso positivo na pratica,
        # mas um autor de regra que confundir os dois operadores obteria
        # `count_gt: 0` == True para qualquer gate ligado.
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, (list, dict, str)):
        return len(value)
    return None


def _apply_operator(op: str, op_value: Any, value: Any) -> bool:
    if op == "absent":
        return _is_absent(value) == bool(op_value)

    if op == "present":
        is_present = not _is_absent(value) and bool(value)
        return is_present == bool(op_value)

    if op == "equals":
        if value is _MISSING:
            return False
        return value == op_value

    if op == "count_gt":
        if value is _MISSING:
            return False
        n = _count(value)
        return n is not None and n > op_value

    if op == "count_eq":
        if value is _MISSING:
            return False
        n = _count(value)
        return n is not None and n == op_value

    if op == "contains":
        if value is _MISSING or not isinstance(value, (list, tuple, str)):
            return False
        return op_value in value

    if op == "any_where":
        if value is _MISSING or not isinstance(value, list):
            return False
        if not isinstance(op_value, dict):
            return False
        return any(
            isinstance(item, dict) and all(item.get(k) == v for k, v in op_value.items())
            for item in value
        )

    raise CatalogError(f"operador de roteamento desconhecido: {op!r}")


def _condition_operator(condition: dict[str, Any]) -> tuple[str, Any]:
    op_keys = [k for k in condition if k in ROUTING_OPERATORS]
    if len(op_keys) != 1:
        raise CatalogError(
            f"condição sem operador reconhecido (ou operador ambíguo): {condition!r}"
        )
    key = op_keys[0]
    return key, condition[key]


def _finding_area(rule_id: str) -> str:
    """Área de um `rule_id`: o prefixo até o último hífen.

    `SF-GLUE-002` -> `SF-GLUE`. É o mesmo agrupamento que separa os coordenadores —
    infra Glue, Athena, PySpark, Iceberg/layout — então a rota de agente conta
    achados por área sem precisar de uma lista de `rule_id` mantida à mão.
    """
    return rule_id.rsplit("-", 1)[0]


def _count_finding_area(finding_ids: frozenset[str], area: str) -> int:
    return sum(1 for fid in finding_ids if _finding_area(fid) == area)


def _eval_condition(
    case: dict[str, Any], finding_ids: frozenset[str], condition: dict[str, Any]
) -> bool:
    if not isinstance(condition, dict):
        raise CatalogError(f"condição de roteamento inválida: {condition!r}")

    has_case = "case" in condition
    has_finding = "finding" in condition
    has_area = "findings_area" in condition
    if has_case + has_finding + has_area != 1:
        raise CatalogError(
            "condição precisa de exatamente um de `case`, `finding` ou "
            f"`findings_area`: {condition!r}"
        )

    op, op_value = _condition_operator(condition)

    if has_case:
        value = _resolve_case_path(case, condition["case"])
    elif has_finding:
        value = True if condition["finding"] in finding_ids else _MISSING
    else:
        value = _count_finding_area(finding_ids, condition["findings_area"])

    return _apply_operator(op, op_value, value)


def _when_matches(
    case: dict[str, Any], finding_ids: frozenset[str], when: dict[str, Any]
) -> bool:
    groups = [g for g in ("all", "any") if g in when]
    if not groups:
        raise CatalogError(f"`when` de roteamento sem grupo `all` nem `any`: {when!r}")

    for group in groups:
        conditions = when.get(group) or []
        if not isinstance(conditions, list):
            raise CatalogError(f"`when.{group}` precisa ser uma lista: {when!r}")
        results = [_eval_condition(case, finding_ids, c) for c in conditions]
        if group == "all" and not all(results):
            return False
        if group == "any" and not any(results):
            return False

    return True

def _evidence_for(rule: dict[str, Any]) -> list[str]:
    when = rule.get("when") or {}
    lines: list[str] = []
    for group in ("all", "any"):
        for condition in when.get(group) or []:
            if "case" in condition:
                subject_kind, subject = "case", condition["case"]
            elif "finding" in condition:
                subject_kind, subject = "finding", condition["finding"]
            else:
                subject_kind, subject = "findings_area", condition.get("findings_area")
            op_keys = [k for k in condition if k in ROUTING_OPERATORS]
            op = op_keys[0] if op_keys else "?"
            lines.append(f"{subject_kind}:{subject} {op}={condition.get(op)}")
    return lines


def _reason_of(rule: dict[str, Any]) -> str:
    return f"{rule['id']}: {str(rule['reason']).strip()}"


def _matching_rules(
    rules: list[dict[str, Any]],
    case: dict[str, Any],
    finding_set: frozenset[str],
    phase: Any,
    key: str,
) -> list[dict[str, Any]]:
    """Regras com `key` presente cujo `phase_in`/`when` casam, na ordem do YAML.

    Mesmo motor de avaliação (`_when_matches`) serve às duas famílias de rota --
    skill (`recommended_skill`) e coordenador (`recommended_agent`, ver AGENT-NNN)
    -- porque a condição é a mesma linguagem declarativa; só o campo projetado
    muda. Isolar por `key` (em vez de um `if "recommended_skill" not in rule:
    continue` genérico) é o que permite às duas famílias conviverem na mesma
    lista de `routing.yaml` sem uma pisar na outra: uma regra `AGENT-*` nunca
    entra em `skill_matches`, e vice-versa -- então `alternatives` (que projeta
    só `recommended_skill`) nunca vê uma regra sem essa chave.
    """
    matches = []
    for rule in rules:
        if key not in rule:
            continue
        phase_in = rule.get("phase_in")
        if phase_in and phase not in phase_in:
            continue
        when = rule.get("when") or {}
        if _when_matches(case, finding_set, when):
            matches.append(rule)
    return matches


def next_step(
    case: dict[str, Any], finding_ids: list[str], directory: Path | None = None
) -> dict[str, Any]:
    """Decide o próximo passo, dado o estado do case e os achados atuais.

    Pura: mesma entrada produz sempre a mesma saída. `finding_ids` é ordenado
    antes de uso, para que a ordem de entrada nunca influencie a resposta.

    Resolve duas rotas independentes sobre o mesmo `routing.yaml`: qual skill
    seguir (`recommended_skill`, regras `ROUTE-*`) e qual coordenador despachar
    (`recommended_agent`, regras `AGENT-*`). São perguntas diferentes -- uma é
    "qual agente investiga", a outra é "qual skill executar agora" -- por isso
    uma pode casar sem a outra, e a ausência de rota de agente não é erro: vira
    `None` com o motivo correspondente também `None`.
    """
    routing = load_routing(directory)
    sorted_ids = sorted(finding_ids)
    finding_set = frozenset(sorted_ids)
    phase = case.get("phase")
    rules = routing["rules"]

    skill_matches = _matching_rules(rules, case, finding_set, phase, "recommended_skill")
    agent_matches = _matching_rules(rules, case, finding_set, phase, "recommended_agent")

    if agent_matches:
        recommended_agent: str | None = agent_matches[0]["recommended_agent"]
        recommended_agent_reason: str | None = _reason_of(agent_matches[0])
    else:
        recommended_agent = None
        recommended_agent_reason = None

    if not skill_matches:
        fallback = routing["fallback"]
        return {
            "phase": phase,
            "recommended_skill": fallback["recommended_skill"],
            "reason": str(fallback["reason"]).strip(),
            "evidence": [],
            "missing_artifacts": [],
            "collect_commands": [],
            "blocked_by": [],
            "alternatives": [],
            "recommended_agent": recommended_agent,
            "recommended_agent_reason": recommended_agent_reason,
        }

    primary = skill_matches[0]
    gates = case.get("gates") or {}
    blocked_by = [g for g in primary.get("blocked_by", []) if not gates.get(g, False)]

    result: dict[str, Any] = {
        "phase": phase,
        "recommended_skill": primary["recommended_skill"],
        "reason": _reason_of(primary),
        "evidence": _evidence_for(primary),
        "missing_artifacts": list(primary.get("missing_artifacts", [])),
        "collect_commands": list(primary.get("collect_commands", [])),
        "blocked_by": blocked_by,
        "alternatives": [
            {
                "rank": rank,
                "rule_id": alt["id"],
                "recommended_skill": alt["recommended_skill"],
                "reason": _reason_of(alt),
            }
            for rank, alt in enumerate(skill_matches[1:], start=2)
        ],
        "recommended_agent": recommended_agent,
        "recommended_agent_reason": recommended_agent_reason,
    }
    if "note" in primary:
        result["note"] = str(primary["note"]).strip()
    return result
