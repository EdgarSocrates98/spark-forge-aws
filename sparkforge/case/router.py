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

from sparkforge.rules.loader import ROUTING_FILE, CatalogError, catalog_dir

ROUTING_OPERATORS = frozenset(
    {"equals", "absent", "present", "count_gt", "count_eq", "contains", "any_where"}
)

_MISSING = object()


def load_routing(directory: Path | None = None) -> dict[str, Any]:
    """Lê `routing.yaml`. Levanta CatalogError se ausente ou malformado."""
    base = directory or catalog_dir()
    path = Path(base) / ROUTING_FILE
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


def _eval_condition(
    case: dict[str, Any], finding_ids: frozenset[str], condition: dict[str, Any]
) -> bool:
    if not isinstance(condition, dict):
        raise CatalogError(f"condição de roteamento inválida: {condition!r}")

    has_case = "case" in condition
    has_finding = "finding" in condition
    if has_case == has_finding:  # nenhum dos dois, ou os dois ao mesmo tempo
        raise CatalogError(
            f"condição precisa de exatamente um de `case` ou `finding`: {condition!r}"
        )

    op, op_value = _condition_operator(condition)

    if has_case:
        value = _resolve_case_path(case, condition["case"])
    else:
        value = True if condition["finding"] in finding_ids else _MISSING

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
            subject_kind = "case" if "case" in condition else "finding"
            subject = condition.get("case", condition.get("finding"))
            op_keys = [k for k in condition if k in ROUTING_OPERATORS]
            op = op_keys[0] if op_keys else "?"
            lines.append(f"{subject_kind}:{subject} {op}={condition.get(op)}")
    return lines


def _reason_of(rule: dict[str, Any]) -> str:
    return f"{rule['id']}: {str(rule['reason']).strip()}"


def next_step(
    case: dict[str, Any], finding_ids: list[str], directory: Path | None = None
) -> dict[str, Any]:
    """Decide o próximo passo, dado o estado do case e os achados atuais.

    Pura: mesma entrada produz sempre a mesma saída. `finding_ids` é ordenado
    antes de uso, para que a ordem de entrada nunca influencie a resposta.
    """
    routing = load_routing(directory)
    sorted_ids = sorted(finding_ids)
    finding_set = frozenset(sorted_ids)
    phase = case.get("phase")

    matches: list[dict[str, Any]] = []
    for rule in routing["rules"]:
        phase_in = rule.get("phase_in")
        if phase_in and phase not in phase_in:
            continue
        when = rule.get("when") or {}
        if _when_matches(case, finding_set, when):
            matches.append(rule)

    if not matches:
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
        }

    primary = matches[0]
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
            for rank, alt in enumerate(matches[1:], start=2)
        ],
    }
    if "note" in primary:
        result["note"] = str(primary["note"]).strip()
    return result
