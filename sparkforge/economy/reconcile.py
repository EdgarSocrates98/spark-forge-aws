"""Reconciliacao canonica das superficies de medicao de economia.

TRES FONTES, NENHUMA SOMA SILENCIOSA. Um mesmo run pode medir tokens de
provider por tres caminhos: o transcript do host (`provider_usage`, a fonte
mais proxima do provider), o `TokenLedger` (`observed_tokens`, o que o host
declarou ao ledger) e os spans do trace (`tokens_status == "measured"`).
Quando duas fontes medem o mesmo eixo e divergem, a resposta e `conflict`
com as duas nomeadas -- escolher uma em silencio seria decidir por heuristica
qual medicao e verdadeira, e nenhuma das duas e estruturalmente prioritaria.

AUTORIDADE POR EIXO, NAO POR MODULO. `payload_bytes` so tem uma autoridade (o
span que o SparkForge mediu). `cost_usd` cruza o `provider_cost` (transcript +
tabela de preco declarada), o ledger (`observed_cost_usd`, que exige
`cost_basis` desde o construtor) e os spans que carregam `cost_basis`.
`tool_calls` cruza ledger e spans de tool.

BASIS DECLARADA POR EIXO. `provider_tokens` soma `input + output +
cache_read + cache_creation` no transcript, `input + output + cached` nos
spans, e `observed_tokens` no ledger -- tres definicoes de "token" que sao
comparadas como candidatas a medir o mesmo eixo. A base vai escrita no
resultado para quem reproduzir a conta chegar no mesmo numero.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

SCHEMA_VERSION = 1

# Chaves de token somadas por fonte, na ordem. A definicao vai junto no
# resultado porque "tokens" sem base e a ambiguidade que esta fase existe
# para remover.
_TRANSCRIPT_TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
)
_SPAN_TOKEN_KEYS = ("input_tokens", "output_tokens", "cached_tokens")


def _sum_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    """Soma os campos numericos presentes; `None` quando nenhum existe."""
    total = 0
    found = False
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            total += int(value)
            found = True
    return total if found else None


def _ledger_value(events: list[Mapping[str, Any]], field: str) -> int | float | None:
    values = [event.get(field) for event in events]
    measured = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not measured:
        return None
    return sum(measured)


def _axis(sources: Mapping[str, int | float | None]) -> dict[str, Any]:
    """Resolve o status de um eixo a partir das fontes declaradas.

    Uma fonte `None` nao e zero -- e "essa fonte nao mediu". Zero medido
    continua sendo zero medido e participa do acordo/conflito como numero.
    """
    measured = {name: value for name, value in sources.items() if value is not None}
    if not measured:
        status = "unresolved"
        authoritative = None
    elif len(set(measured.values())) == 1:
        status = "measured"
        authoritative = next(iter(measured.values()))
    else:
        status = "conflict"
        authoritative = None
    return {
        "status": status,
        "authoritative": authoritative,
        "sources": dict(sources),
    }


def _spans(trace: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if not trace:
        return []
    spans = trace.get("spans")
    return [s for s in spans if isinstance(s, Mapping)] if isinstance(spans, list) else []


def _events(
    ledger_events: Iterable[Any],
) -> list[Mapping[str, Any]]:
    """Normaliza `LedgerEvent` (objeto) ou mapping serializado para dict."""
    out: list[Mapping[str, Any]] = []
    for event in ledger_events:
        if hasattr(event, "to_dict"):
            out.append(event.to_dict())
        elif isinstance(event, Mapping):
            out.append(event)
    return out


def _trace_measured_tokens(spans: list[Mapping[str, Any]]) -> int | None:
    """Soma tokens so sobre spans `measured`; `None` quando nenhum mediu."""
    from sparkforge.observability.tracer import tokens_status_of

    total = 0
    found = False
    for span in spans:
        declared = span.get("tokens_status") or ""
        status = tokens_status_of(
            str(span.get("component_type", "")),
            int(span.get("input_tokens") or 0),
            int(span.get("output_tokens") or 0),
            int(span.get("cached_tokens") or 0),
            declared=declared,
        )
        if status == "measured":
            total += int(span.get("input_tokens") or 0) + int(span.get("output_tokens") or 0)
            total += int(span.get("cached_tokens") or 0)
            found = True
    return total if found else None


def _trace_measured_cost(spans: list[Mapping[str, Any]]) -> float | None:
    """Custo so conta onde existe `cost_basis`; sem fonte nao e medicao."""
    total = 0.0
    found = False
    for span in spans:
        if span.get("cost_basis"):
            total += float(span.get("estimated_cost_usd") or 0.0)
            found = True
    return round(total, 6) if found else None


def reconcile_run_economy(
    *,
    trace: Mapping[str, Any] | None = None,
    ledger_events: Iterable[Any] = (),
    provider_usage: Mapping[str, Any] | None = None,
    provider_cost: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Cruza as fontes de medicao de um run por eixo.

    Args:
        trace: o que `SQLiteTraceStore.get_trace()` devolve (ou o dict
            equivalente com `spans`).
        ledger_events: `LedgerEvent`s ou mappings com os mesmos campos.
        provider_usage: dict de usage do host (ex.: `provider_cost()["tokens"]`
            ou `read_host_usage()`), chaves em `_TRANSCRIPT_TOKEN_KEYS`.
        provider_cost: resultado de `economy.provider_cost.provider_cost()`.

    Returns:
        `{"axes": {...}, "unresolved": [...], "conflicts": [...]}` com status
        `measured`/`conflict`/`unresolved` por eixo. `authoritative` so carrega
        numero quando toda fonte que mediu concorda; divergencia sai `conflict`
        com as fontes em `sources`.
    """
    spans = _spans(trace)
    events = _events(ledger_events)

    axes = {
        "provider_tokens": _axis(
            {
                "transcript": (
                    _sum_keys(provider_usage, _TRANSCRIPT_TOKEN_KEYS)
                    if provider_usage
                    else None
                ),
                "ledger": _ledger_value(events, "observed_tokens"),
                "trace": _trace_measured_tokens(spans),
            }
        ),
        "cost_usd": _axis(
            {
                "provider_cost": (
                    provider_cost.get("cost_usd") if provider_cost else None
                ),
                "ledger": _ledger_value(events, "observed_cost_usd"),
                "trace": _trace_measured_cost(spans),
            }
        ),
        "tool_calls": _axis(
            {
                "ledger": _ledger_value(events, "observed_tool_calls"),
                "trace": (
                    sum(1 for s in spans if s.get("component_type") == "tool")
                    if any(s.get("component_type") == "tool" for s in spans)
                    else None
                ),
            }
        ),
        "payload_bytes": _axis(
            {
                "trace": (
                    sum(int(s.get("payload_bytes") or 0) for s in spans)
                    if spans
                    else None
                )
            }
        ),
    }
    axes["provider_tokens"]["basis"] = {
        "transcript": list(_TRANSCRIPT_TOKEN_KEYS),
        "trace": list(_SPAN_TOKEN_KEYS),
        "ledger": ["observed_tokens"],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "axes": axes,
        "unresolved": [name for name, axis in axes.items() if axis["status"] == "unresolved"],
        "conflicts": [name for name, axis in axes.items() if axis["status"] == "conflict"],
    }


__all__ = ["reconcile_run_economy"]
