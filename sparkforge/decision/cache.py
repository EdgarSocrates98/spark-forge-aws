"""Bounded in-process cache for deterministic decisions."""

from __future__ import annotations

from collections import OrderedDict

from sparkforge.decision.models import DecisionResult


class DecisionCache:
    def __init__(self, max_entries: int = 128) -> None:
        if isinstance(max_entries, bool) or max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._items: OrderedDict[str, DecisionResult] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, fingerprint: str) -> DecisionResult | None:
        value = self._items.get(fingerprint)
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        self._items.move_to_end(fingerprint)
        return value

    def put(self, fingerprint: str, result: DecisionResult) -> None:
        self._items[fingerprint] = result.with_cache_hit(False)
        self._items.move_to_end(fingerprint)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)
            self.evictions += 1

    def invalidate(self, fingerprint: str | None = None) -> None:
        if fingerprint is None:
            self._items.clear()
        else:
            self._items.pop(fingerprint, None)

    def clear(self) -> None:
        self.invalidate()

    def __len__(self) -> int:
        return len(self._items)

    def stats(self) -> dict[str, int]:
        return {
            "entries": len(self._items),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
        }


__all__ = ["DecisionCache"]
