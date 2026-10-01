"""Empacotamento de contexto com deduplicacao e prioridade por tipo.

Fato e decisao entram antes de snapshot e task porque sao o que sustenta um
achado. O corte por `max_items` e reportado em `truncated` em vez de silencioso:
contexto descartado sem aviso vira evidencia que some.
"""
from collections import OrderedDict


def pack_context(messages, max_items=24):
    priority = {"fact": 0, "decision": 1, "snapshot": 2, "task": 3}
    unique = OrderedDict()
    for msg in messages:
        kind = str(msg.get("kind", "task"))
        content = str(msg.get("content", msg.get("text", ""))).strip()
        unique[(kind, content, str(msg.get("source", "")))] = {
            **msg,
            "kind": kind,
            "content": content,
        }
    ranked = sorted(
        unique.values(),
        key=lambda x: (priority.get(x["kind"], 9), -len(x["content"])),
    )
    selected = ranked[:max_items]
    return {
        "messages": selected,
        "selected": len(selected),
        "deduplicated": len(messages) - len(unique),
        "truncated": max(0, len(ranked) - max_items),
    }
