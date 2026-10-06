"""Local-first AgentOps inspection, comparison and baseline regression checks."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.observability.tracer import tokens_status_of

_TOKEN_FIELDS = ("input_tokens", "output_tokens", "cached_tokens")


def _load_trace(db_path: Path | str, run_id: str) -> dict[str, Any] | None:
    path = Path(db_path)
    if not path.exists():
        return None
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        trace = conn.execute("SELECT * FROM traces WHERE run_id = ?", (run_id,)).fetchone()
        if trace is None:
            return None
        result = dict(trace)
        result["spans"] = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM spans WHERE run_id = ? ORDER BY start_time", (run_id,)
            )
        ]
        return result


@dataclass(frozen=True, slots=True)
class WasteAttribution:
    pattern: str
    classification: str
    evidence: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "classification": self.classification,
            "evidence": list(self.evidence),
            "description": self.description,
        }


def _waste(spans: list[dict[str, Any]]) -> list[WasteAttribution]:
    findings: list[WasteAttribution] = []
    seen: dict[str, list[str]] = {}
    for span in spans:
        if span.get("component_type") == "tool":
            key = f"{span.get('name')}:{span.get('metadata_json', '')}"
            seen.setdefault(key, []).append(str(span.get("span_id")))
    for key, ids in seen.items():
        if len(ids) > 1:
            findings.append(
                WasteAttribution(
                    "duplicate_tool_call",
                    "observed",
                    tuple(ids),
                    f"tool call repeated {len(ids)} times: {key[:100]}",
                )
            )
    for span in spans:
        metadata = span.get("metadata_json") or "{}"
        try:
            data = json.loads(metadata) if isinstance(metadata, str) else metadata
        except json.JSONDecodeError:
            data = {}
        if data.get("tier") in {"tier_5_premium", "premium"} and data.get("task_complexity") in {
            "low",
            "deterministic",
        }:
            findings.append(
                WasteAttribution(
                    "premium_model_on_simple_task",
                    "hypothesis",
                    (str(span.get("span_id")),),
                    "routing metadata suggests premium model may be unnecessary",
                )
            )
        if span.get("payload_bytes", 0) and span.get("item_count") == 0:
            findings.append(
                WasteAttribution(
                    "empty_context_payload",
                    "observed",
                    (str(span.get("span_id")),),
                    "tool emitted payload bytes with no returned items",
                )
            )
    return findings


def _span_tokens_status(span: dict[str, Any]) -> str:
    """Status de medicao lido da linha, ou derivado quando a coluna vem NULL
    de um banco escrito antes dela existir."""
    declared = span.get("tokens_status") or ""
    if declared:
        return tokens_status_of(
            str(span.get("component_type", "")), 0, 0, 0, declared=declared
        )
    return tokens_status_of(
        str(span.get("component_type", "")),
        int(span.get("input_tokens") or 0),
        int(span.get("output_tokens") or 0),
        int(span.get("cached_tokens") or 0),
    )


def _axis_status(measured: int, unresolved: int) -> str:
    if measured and unresolved:
        return "partial"
    if measured:
        return "measured"
    if unresolved:
        return "unresolved"
    return "not_applicable"


def _provider_usage_coverage(spans: list[dict[str, Any]]) -> dict[str, Any]:
    """§12: measured/total de spans de modelo -- cobertura de observacao de
    provider, nao consumo. Sem span de modelo, `coverage` e `unresolved`
    (0/0 nao e 100% nem 0%)."""
    modelos = [s for s in spans if s.get("component_type") == "model"]
    if not modelos:
        return {"measured": 0, "total": 0, "coverage": "unresolved"}
    measured = sum(1 for s in modelos if _span_tokens_status(s) == "measured")
    return {
        "measured": measured,
        "total": len(modelos),
        "coverage": round(measured / len(modelos), 6),
    }


def _model_axes(spans: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Os dois eixos de modelo, medidos por span e nunca somados com ausencia.

    `observed` so carrega numero quando ao menos um span mediu; `partial`
    significa que a soma cobre so os spans medidos, e o buraco e nomeado pelo
    status em vez de sumir dentro de um zero."""
    tokens_measured = tokens_unresolved = 0
    tokens_observed = 0
    cost_measured = cost_unresolved = 0
    cost_observed = 0.0
    for span in spans:
        status = _span_tokens_status(span)
        if status == "measured":
            tokens_measured += 1
            tokens_observed += sum(int(span.get(f) or 0) for f in _TOKEN_FIELDS)
        elif status == "unresolved":
            tokens_unresolved += 1
        if span.get("cost_basis"):
            cost_measured += 1
            cost_observed += float(span.get("estimated_cost_usd") or 0.0)
        elif span.get("component_type") == "model":
            cost_unresolved += 1
    return {
        "tokens": {
            "observed": tokens_observed if tokens_measured else None,
            "status": _axis_status(tokens_measured, tokens_unresolved),
        },
        "cost": {
            "observed": round(cost_observed, 6) if cost_measured else None,
            "status": _axis_status(cost_measured, cost_unresolved),
        },
    }


def inspect_run(
    db_path: Path | str,
    run_id: str,
    *,
    ledger_events: Any = (),
    provider_usage: Any = None,
    provider_cost: Any = None,
) -> dict[str, Any]:
    trace = _load_trace(db_path, run_id)
    if trace is None:
        return {"status": "unresolved", "run_id": run_id, "unresolved": ["run_not_found"]}
    spans = trace.get("spans", [])
    by_component: dict[str, int] = {}
    for span in spans:
        component = str(span.get("component_type", "unknown"))
        by_component[component] = by_component.get(component, 0) + 1
    evidence = sorted({ref for span in spans for ref in _metadata_list(span, "evidence_refs")})
    unresolved = sorted({ref for span in spans for ref in _metadata_list(span, "unresolved")})
    model_axes = _model_axes(spans)
    unresolved = sorted(
        {
            *unresolved,
            *(
                "model_tokens_unresolved"
                for axis in (model_axes["tokens"],)
                if axis["status"] in {"unresolved", "partial"}
            ),
            *(
                "model_cost_unresolved"
                for axis in (model_axes["cost"],)
                if axis["status"] in {"unresolved", "partial"}
            ),
        }
    )
    return {
        "status": "ok",
        "run": {
            key: trace.get(key)
            for key in ("run_id", "task_description", "profile", "status", "start_time", "end_time")
        },
        "spans": {"count": len(spans), "by_component": by_component},
        "context": {
            "bytes": sum(int(span.get("payload_bytes") or 0) for span in spans),
            "tokens": "tokens_unresolved",
            "duplicates": sum(
                1 for finding in _waste(spans) if finding.pattern == "duplicate_tool_call"
            ),
        },
        "models": {
            "calls": by_component.get("model", 0),
            **model_axes,
            "provider_usage_coverage": _provider_usage_coverage(spans),
        },
        # A reconciliacao por eixo cruza trace + ledger + transcript; quando o
        # chamador nao passa ledger/transcript, as fontes saem `None` -- a
        # ausencia e declarada, nao preenchida.
        "economy": _reconcile(trace, ledger_events, provider_usage, provider_cost),
        "evidence": {"refs": evidence, "count": len(evidence), "unresolved": unresolved},
        "waste": [finding.to_dict() for finding in _waste(spans)],
    }


def _reconcile(
    trace: dict[str, Any],
    ledger_events: Any,
    provider_usage: Any,
    provider_cost: Any,
) -> dict[str, Any]:
    """Import preguicoso: `economy/__init__` arrasta decision_plane e governor,
    e agentops fica no caminho de importacao de `_core` -- a fusao e barata,
    o custo de import nao."""
    from sparkforge.economy.reconcile import reconcile_run_economy

    return reconcile_run_economy(
        trace=trace,
        ledger_events=ledger_events,
        provider_usage=provider_usage,
        provider_cost=provider_cost,
    )


def _metadata_list(span: dict[str, Any], key: str) -> list[str]:
    raw = span.get("metadata_json") or "{}"
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return []
    values = data.get(key, []) if isinstance(data, dict) else []
    return [str(value) for value in values] if isinstance(values, list) else []


_TIMELINE_LANES = frozenset(
    {
        "task",
        "context",
        "routing",
        "agent",
        "model",
        "tool",
        "review",
        "debate",
        "checkpoint",
        "eval",
        "gate",
    }
)


def run_timeline(db_path: Path | str, run_id: str) -> dict[str, Any]:
    """Linha do tempo do run: eventos ordenados por `start_time` com lane.

    `lane` e o component_type quando ele esta no vocabulario §68; qualquer
    componente fora dele vira "other" nomeado -- nunca descartado.
    """
    trace = _load_trace(db_path, run_id)
    if trace is None:
        return {
            "status": "unresolved",
            "run_id": run_id,
            "unresolved": ["run_not_found"],
        }
    eventos = []
    for span in trace.get("spans", []):
        componente = str(span.get("component_type", "unknown"))
        eventos.append(
            {
                "span_id": span.get("span_id"),
                "name": span.get("name"),
                "lane": componente if componente in _TIMELINE_LANES else "other",
                "component_type": componente,
                "start_time": span.get("start_time"),
                "end_time": span.get("end_time"),
                "duration_seconds": span.get("duration_seconds"),
                "tokens_status": _span_tokens_status(span),
                "outcome": span.get("outcome"),
            }
        )
    return {
        "status": "ok",
        "run_id": run_id,
        "events": eventos,
        "count": len(eventos),
    }


def critical_path(db_path: Path | str, run_id: str) -> dict[str, Any]:
    """Caminho critico medido, nao CPM: os spans que mais contribuiram para
    a duracao observada do run.

    Nao e o critical path do metodo CPM — isso exigiria um grafo de
    dependencias que o ledger nao guarda. O que sai daqui e o perfil de
    duracao medido: os `top` spans por `duration_seconds`, retries por nome
    repetido e `waiting_seconds` (gaps entre `end_time` consecutivos). Tudo
    observado de `duration_seconds`/timestamps -- sem latencia inventada.
    """
    trace = _load_trace(db_path, run_id)
    if trace is None:
        return {
            "status": "unresolved",
            "run_id": run_id,
            "unresolved": ["run_not_found"],
        }
    spans = sorted(
        trace.get("spans", []),
        key=lambda s: (s.get("start_time") or 0.0),
    )
    top = sorted(
        spans,
        key=lambda s: float(s.get("duration_seconds") or 0.0),
        reverse=True,
    )[:5]
    retries: dict[str, int] = {}
    for span in spans:
        nome = str(span.get("name"))
        retries[nome] = retries.get(nome, 0) + 1
    retries = {nome: n for nome, n in retries.items() if n > 1}
    waiting = 0.0
    for anterior, seguinte in zip(spans, spans[1:], strict=False):
        fim = anterior.get("end_time")
        inicio = seguinte.get("start_time")
        if fim is not None and inicio is not None and inicio > fim:
            waiting += inicio - fim
    return {
        "status": "ok",
        "run_id": run_id,
        "top": [
            {
                "span_id": span.get("span_id"),
                "name": span.get("name"),
                "component_type": span.get("component_type"),
                "duration_seconds": span.get("duration_seconds"),
            }
            for span in top
        ],
        "retries": retries,
        "waiting_seconds": round(waiting, 6),
    }


def compare_runs(db_path: Path | str, run_a: str, run_b: str) -> dict[str, Any]:
    left = inspect_run(db_path, run_a)
    right = inspect_run(db_path, run_b)
    if left.get("status") != "ok" or right.get("status") != "ok":
        return {
            "status": "unresolved",
            "left": left,
            "right": right,
            "unresolved": ["run_not_found"],
        }

    def delta(path: tuple[str, ...]) -> float:
        def read(payload: dict[str, Any]) -> float:
            current: Any = payload
            for part in path:
                current = current[part]
            return float(current)

        return read(right) - read(left)

    def axis_delta(axis: str, unresolved_label: str) -> float | str:
        left_observed = left["models"][axis]["observed"]
        right_observed = right["models"][axis]["observed"]
        if left_observed is None or right_observed is None:
            return unresolved_label
        return right_observed - left_observed

    return {
        "status": "ok",
        "run_a": run_a,
        "run_b": run_b,
        "delta": {
            "context_bytes": delta(("context", "bytes")),
            "model_calls": delta(("models", "calls")),
            "tokens": axis_delta("tokens", "tokens_unresolved"),
            "cost": axis_delta("cost", "cost_unresolved"),
            "evidence_count": delta(("evidence", "count")),
        },
        "quality": {"evidence_recall": "unresolved_without_task_contract"},
        "unresolved": ["provider_tokens_missing", "task_quality_contract_missing"],
    }


def save_baseline(db_path: Path | str, run_id: str, baseline_path: Path | str) -> dict[str, Any]:
    report = inspect_run(db_path, run_id)
    destination = Path(baseline_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {"run_id": run_id, "report": report}, ensure_ascii=True, sort_keys=True, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    return {"status": "ok", "path": str(destination), "run_id": run_id, "report": report}


def compare_baseline(db_path: Path | str, run_id: str, baseline_path: Path | str) -> dict[str, Any]:
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    return compare_runs(db_path, str(baseline["run_id"]), run_id)


__all__ = [
    "WasteAttribution",
    "compare_baseline",
    "compare_runs",
    "critical_path",
    "inspect_run",
    "run_timeline",
    "save_baseline",
]
