"""Append-only conversation room for cooperative agents."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .budget import select_context

MESSAGE_TYPES = {
    "task",
    "fact",
    "hypothesis",
    "challenge",
    "handoff",
    "decision",
    "error",
    "snapshot",
}

@dataclass(frozen=True)
class Message:
    room_id: str
    author: str
    kind: str
    phase: str
    content: dict[str, Any]
    refs: tuple[str, ...] = ()
    created_at: float = field(default_factory=time.time)

    def to_record(self) -> dict[str, Any]:
        data = asdict(self)
        data["refs"] = list(self.refs)
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        data["message_id"] = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return data

class ConversationRoom:
    def __init__(self, root: str | Path, room_id: str, max_messages: int = 500):
        self.path = Path(root) / f"{room_id}.jsonl"
        self.room_id = room_id
        self.max_messages = max_messages
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        author: str,
        kind: str,
        phase: str,
        content: dict[str, Any],
        refs: Iterable[str] = (),
    ) -> str:
        if kind not in MESSAGE_TYPES:
            raise ValueError(f"unsupported message kind: {kind}")
        record = Message(self.room_id, author, kind, phase, content, tuple(refs)).to_record()
        if len(self.records()) >= self.max_messages:
            raise RuntimeError("room message budget exhausted; compact before appending")
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record["message_id"]

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def context(
        self,
        *,
        phase: str | None = None,
        limit: int = 24,
        query: str = "",
        token_budget: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.records()
        if phase:
            phase_rows = [
                row
                for row in rows
                if row.get("phase") == phase or row.get("kind") in {"decision", "snapshot"}
            ]
            rows = phase_rows or rows
        rows = rows[-limit:]
        if query and token_budget is not None:
            return select_context(rows, query, token_budget)
        return rows

    def render_trace(self, enabled: bool = False, show_content: bool = False) -> dict[str, Any]:
        from .observability import TraceEvent, TraceView, Usage
        trace = TraceView(enabled=enabled, show_content=show_content)
        for row in self.records():
            raw = row.get("usage") or {}
            usage = (
                Usage(
                    input_tokens=raw.get("input_tokens"),
                    output_tokens=raw.get("output_tokens"),
                    total_tokens=raw.get("total_tokens"),
                    estimated=bool(raw.get("estimated", False)),
                )
                if raw
                else None
            )
            trace.record(
                TraceEvent(
                    row.get("message_id", ""),
                    row.get("author", ""),
                    row.get("kind", ""),
                    row.get("phase", ""),
                    str(row.get("content", {})),
                    usage,
                )
            )
        return trace.render()

    def compact(self, summary: dict[str, Any], author: str = "room-compactor") -> str:
        rows = self.records()
        refs = [row["message_id"] for row in rows[-64:] if "message_id" in row]
        return self.append(
            author,
            "snapshot",
            "compaction",
            {"summary": summary, "covered": len(rows)},
            refs,
        )

