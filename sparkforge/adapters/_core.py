"""Logica compartilhada entre a CLI (`cli.py`) e a superficie MCP (`tools.py`).

Adaptador fino: nenhuma funcao aqui decide limiar, severidade ou rota. Tudo
delega para `sparkforge.facts`, `sparkforge.rules`, `sparkforge.case` e
`sparkforge.findings`. Isto existe para que a CLI e o servidor MCP nunca
divirjam -- os dois chamam exatamente as mesmas funcoes deste modulo.

`AdapterError` e o unico tipo de erro que atravessa a fronteira do adaptador:
`cli.py` o traduz em (stderr, exit code); `tools.py` o traduz em um dict
`{"error": ...}`. Erros de baixo nivel (`CaseError`, `CatalogError`,
`ValidationFailed`) sao capturados aqui e reembalados, nunca vazam crus.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.case import router, store
from sparkforge.case.resume import render_handoff
from sparkforge.case.resume import resume as run_resume
from sparkforge.facts.pyspark_ast import extract_path, extract_tree
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.findings.models import Fact, RuntimeContext
from sparkforge.findings.validate import ValidationFailed, validate_finding
from sparkforge.rules.engine import judge as run_judge
from sparkforge.rules.loader import CatalogError, load_catalog

DEFAULT_LIMIT = 50


class AdapterError(Exception):
    """Erro acionavel de fronteira: mensagem pronta para stderr ou para um
    dict `{"error": ...}`, mais o exit code que a CLI deve devolver."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def _count_by(items: list[Any], keyfn: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = keyfn(item)
        counts[key] = counts.get(key, 0) + 1
    return counts


def paginate_items(
    items: list[Any], limit: int | None, cursor: str | None
) -> tuple[list[Any], str | None]:
    """Fatia `items` (ja filtrado) em uma pagina. `limit=None` devolve tudo.

    Cursor e um offset inteiro codificado como string -- suficiente porque a
    ordenacao upstream (sort_facts/sort_findings/ordem do catalogo) ja e
    deterministica, entao o mesmo cursor sempre reproduz a mesma pagina.
    """
    try:
        start = int(cursor) if cursor else 0
    except ValueError as exc:
        raise AdapterError(f"cursor invalido: {cursor!r}", exit_code=2) from exc
    if start < 0:
        raise AdapterError(f"cursor invalido: {cursor!r}", exit_code=2)

    if limit is None:
        return items[start:], None

    end = start + limit
    page = items[start:end]
    next_cursor = str(end) if end < len(items) else None
    return page, next_cursor


def build_runtime_context(
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
) -> RuntimeContext:
    raw = {
        "glue_version": glue,
        "spark_version": spark,
        "python_version": python,
        "iceberg_version": iceberg,
        "athena_version": athena,
    }
    cleaned = {k: v for k, v in raw.items() if v}
    sources = {"cli": cleaned} if cleaned else {}
    context, _facts = detect_runtime(sources)
    return context


# --------------------------------------------------------------------------- #
# analyze pyspark
# --------------------------------------------------------------------------- #


def _extract_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(f"Caminho nao encontrado para analise: {path}", exit_code=2)
    if target.is_dir():
        return extract_tree(target, repo_root=target)
    return extract_path(target, repo_root=target.parent)


def analyze_pyspark(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_facts(path)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)

    # `unresolved` e contado sobre `facts`, nao sobre `filtered`: um filtro por
    # kind nao pode fazer o ponto cego desaparecer do relatorio. A regra 7 do
    # AGENT_PROTOCOL.md exige reportar sempre — no nao resolvido e ponto cego,
    # nao ausencia de problema, e omiti-lo deixa o operador confundir "nao achei"
    # com "nao ha".
    unresolved = sum(1 for f in facts if f.kind == "pyspark.unresolved")
    unresolved_at = [
        {
            "file": f.subject.get("file", ""),
            "line": f.subject.get("line", 0),
            "reason": f.attrs.get("reason", ""),
        }
        for f in facts
        if f.kind == "pyspark.unresolved"
    ]

    return {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "unresolved": unresolved,
        "unresolved_at": unresolved_at,
        "items": page,
    }


# --------------------------------------------------------------------------- #
# judge
# --------------------------------------------------------------------------- #


def _facts_from_dicts(payload: Any) -> list[Fact]:
    if not isinstance(payload, list):
        raise AdapterError("facts precisa ser uma lista de objetos fact.", exit_code=2)

    facts: list[Fact] = []
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise AdapterError(f"facts[{index}] nao e um objeto.", exit_code=2)
        try:
            kwargs: dict[str, Any] = {"kind": entry["kind"], "subject": entry["subject"]}
        except KeyError as exc:
            raise AdapterError(
                f"facts[{index}] esta sem o campo obrigatorio {exc}. O arquivo de facts "
                "pode ter sido gerado por uma versao antiga do schema. Rode "
                "`sparkforge analyze pyspark --path <dir> --out <arquivo>` novamente.",
                exit_code=2,
            ) from exc
        for optional in ("measures", "attrs", "provenance", "schema_version"):
            if optional in entry:
                kwargs[optional] = entry[optional]
        facts.append(Fact(**kwargs))
    return facts


def _load_facts_file(facts_path: str) -> list[Fact]:
    path = Path(facts_path)
    if not path.is_file():
        raise AdapterError(
            f"Arquivo de facts nao encontrado: {facts_path}. Rode "
            f"`sparkforge analyze pyspark --path <dir> --out {facts_path}` para gera-lo.",
            exit_code=2,
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterError(f"{facts_path}: JSON invalido: {exc}", exit_code=2) from exc
    return _facts_from_dicts(raw)


def judge_findings(
    facts: list[dict[str, Any]] | None = None,
    facts_path: str | None = None,
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
    severity: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    show_skipped: bool = False,
) -> dict[str, Any]:
    if facts is not None:
        fact_list = _facts_from_dicts(facts)
    elif facts_path is not None:
        fact_list = _load_facts_file(facts_path)
    else:
        raise AdapterError(
            "informe `facts` (lista inline de facts) ou `facts_path` (arquivo gerado por "
            "`sparkforge analyze pyspark --out <arquivo>`).",
            exit_code=2,
        )

    try:
        rules = load_catalog()
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    context = build_runtime_context(glue, spark, python, iceberg, athena)
    runtime = context.to_dict()

    findings, skipped = run_judge(fact_list, rules, runtime, return_skipped=True)
    finding_dicts = [f.to_dict() for f in findings]

    if severity:
        wanted = set(severity)
        finding_dicts = [f for f in finding_dicts if f["severity"] in wanted]

    by_severity = _count_by(finding_dicts, lambda f: f["severity"])
    page, next_cursor = paginate_items(finding_dicts, limit, cursor)

    result: dict[str, Any] = {
        "total_count": len(finding_dicts),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "severity": list(severity) if severity else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_severity": by_severity,
        "items": page,
    }
    if show_skipped:
        result["skipped"] = skipped
    return result


# --------------------------------------------------------------------------- #
# runtime detect
# --------------------------------------------------------------------------- #


def runtime_detect(
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
) -> dict[str, Any]:
    return build_runtime_context(glue, spark, python, iceberg, athena).to_dict()


# --------------------------------------------------------------------------- #
# rules lookup
# --------------------------------------------------------------------------- #


def rules_lookup(
    id: list[str] | None = None,  # noqa: A002 -- nome do parametro espelha o flag --id
    category: str | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    try:
        rules = load_catalog()
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    filtered = rules
    if id:
        wanted_ids = set(id)
        filtered = [r for r in filtered if r["id"] in wanted_ids]
    if category:
        filtered = [r for r in filtered if r.get("category") == category]

    by_category = _count_by(filtered, lambda r: r.get("category", ""))
    clean = [{k: v for k, v in r.items() if k != "_source_file"} for r in filtered]
    page, next_cursor = paginate_items(clean, limit, cursor)

    return {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "id": list(id) if id else None,
            "category": category,
            "limit": limit,
            "cursor": cursor,
        },
        "by_category": by_category,
        "rules": page,
    }


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #


def validate_output(finding: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_finding(finding)
        return {"valid": True, "errors": []}
    except ValidationFailed as exc:
        return {"valid": False, "errors": [str(exc)]}


# --------------------------------------------------------------------------- #
# case lifecycle
# --------------------------------------------------------------------------- #


def case_open(
    repo: str,
    case_id: str,
    now: str,
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
) -> dict[str, Any]:
    context = build_runtime_context(glue, spark, python, iceberg, athena)
    case = store.new_case(case_id, now, context.to_dict(), repo=repo)
    store.save_case(case, root=repo)
    return case


def case_get(repo: str) -> dict[str, Any]:
    try:
        return store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def case_update(
    repo: str,
    phase: str | None = None,
    gate: str | None = None,
    gate_value: bool = True,
    skill: str | None = None,
    now: str | None = None,
    outcome: str | None = None,
) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
        if phase is not None:
            case = store.set_phase(case, phase)
        if gate is not None:
            case = store.set_gate(case, gate, bool(gate_value))
        if skill is not None:
            case = store.record_skill_use(case, skill, now or "", outcome or "")
        store.save_case(case, root=repo)
        return case
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def next_step(repo: str, findings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    finding_ids = [
        f.get("rule_id") for f in (findings or []) if isinstance(f, dict) and f.get("rule_id")
    ]
    try:
        return router.next_step(case, finding_ids)
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def resume_case(
    repo: str,
    findings: list[dict[str, Any]] | None = None,
    unresolved: int = 0,
    in_flight: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    try:
        return run_resume(
            case, findings or [], unresolved_count=unresolved, in_flight=in_flight, root=root
        )
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def handoff(
    repo: str,
    findings: list[dict[str, Any]] | None = None,
    unresolved: int = 0,
    in_flight: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    payload = resume_case(repo, findings, unresolved, in_flight, root=root)
    markdown = render_handoff(payload)
    path = Path(repo) / ".sparkforge" / "handoff.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    result = dict(payload)
    result["handoff_path"] = str(path)
    return result
