"""Optional observability for agent handoffs and token usage."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated: bool = False

@dataclass(frozen=True)
class TraceEvent:
    event_id: str
    actor: str
    event_type: str
    phase: str
    summary: str
    usage: Usage | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class TraceView:
    def __init__(self, enabled: bool = False, show_content: bool = False):
        self.enabled = enabled
        self.show_content = show_content
        self._events: list[TraceEvent] = []

    def record(self, event: TraceEvent) -> None:
        if self.enabled:
            self._events.append(event)

    def events(self) -> list[TraceEvent]:
        return list(self._events)

    def render(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "events": [], "notice": "trace view disabled"}
        total = 0
        known = True
        rendered = []
        for event in self._events:
            usage = None
            if event.usage is not None:
                usage = {
                    "input_tokens": event.usage.input_tokens,
                    "output_tokens": event.usage.output_tokens,
                    "total_tokens": event.usage.total_tokens,
                    "estimated": event.usage.estimated,
                }
                if event.usage.total_tokens is None:
                    known = False
                else:
                    total += event.usage.total_tokens
            rendered.append(
                {
                    "event_id": event.event_id,
                    "actor": event.actor,
                    "event_type": event.event_type,
                    "phase": event.phase,
                    "summary": (
                        event.summary if self.show_content else event.summary[:160]
                    ),
                    "usage": usage,
                }
            )
        notice = (
            "token usage available from runtime"
            if known
            else "token usage unavailable or partial; values may be estimated"
        )
        return {
            "enabled": True,
            "events": rendered,
            "total_tokens": total if known else None,
            "token_notice": notice,
        }
