"""Bounded caches with explicit namespaces and ownership metadata."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from sparkforge.decision.models import DecisionResult


class CacheKind(str, Enum):
    FACT = "fact"
    DECISION = "decision"
    ARTIFACT = "artifact"


@dataclass(frozen=True, slots=True)
class CacheKey:
    kind: CacheKind
    version: int
    components: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.components or any(not str(item).strip() for item in self.components):
            raise ValueError("cache key components must be non-empty")

    def canonical(self) -> str:
        return "|".join((self.kind.value, str(self.version), *self.components))


@dataclass(frozen=True, slots=True)
class CacheRecord:
    key: CacheKey
    value: Any
    owner: str
    freshness: str = "fresh"
    invalidation_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_kind": self.key.kind.value,
            "key_fingerprint": self.key.canonical(),
            "owner": self.owner,
            "freshness": self.freshness,
            "invalidation_reason": self.invalidation_reason,
        }


T = TypeVar("T")


class _NamespacedCache(Generic[T]):
    def __init__(self, kind: CacheKind, max_entries: int = 128) -> None:
        if isinstance(max_entries, bool) or max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.kind = kind
        self.max_entries = max_entries
        self._items: OrderedDict[str, CacheRecord] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.invalidations = 0
        self.last_invalidation_reason: str | None = None

    def get(self, key: CacheKey) -> CacheRecord | None:
        self._validate_key(key)
        record = self._items.get(key.canonical())
        if record is None:
            self.misses += 1
            return None
        self.hits += 1
        self._items.move_to_end(key.canonical())
        return record

    def get_owned(
        self,
        key: CacheKey,
        *,
        owner: str,
        freshness: str = "fresh",
    ) -> CacheRecord | None:
        """Return a record only when namespace, owner and freshness agree."""
        if not owner.strip():
            raise ValueError("cache owner is required")
        record = self.get(key)
        if record is None:
            return None
        if record.owner != owner or record.freshness != freshness:
            self.invalidate(key, reason="owner_or_freshness_mismatch")
            return None
        return record

    def put(
        self,
        key: CacheKey,
        value: T,
        *,
        owner: str,
        freshness: str = "fresh",
    ) -> CacheRecord:
        self._validate_key(key)
        if not owner.strip():
            raise ValueError("cache owner is required")
        record = CacheRecord(key, value, owner, freshness)
        self._items[key.canonical()] = record
        self._items.move_to_end(key.canonical())
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)
            self.evictions += 1
        return record

    def invalidate(self, key: CacheKey | None = None, *, reason: str = "explicit") -> None:
        if not reason.strip():
            raise ValueError("cache invalidation reason is required")
        self.invalidations += 1
        self.last_invalidation_reason = reason
        if key is None:
            self._items.clear()
            return
        self._validate_key(key)
        self._items.pop(key.canonical(), None)

    def stats(self) -> dict[str, int | str]:
        return {
            "cache_kind": self.kind.value,
            "entries": len(self._items),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "last_invalidation_reason": self.last_invalidation_reason,
        }

    def _validate_key(self, key: CacheKey) -> None:
        if key.kind is not self.kind:
            raise ValueError(f"cache namespace mismatch: expected {self.kind.value}")


class FactCache(_NamespacedCache[Any]):
    def __init__(self, max_entries: int = 128) -> None:
        super().__init__(CacheKind.FACT, max_entries)


class ArtifactCache(_NamespacedCache[Any]):
    def __init__(self, max_entries: int = 128) -> None:
        super().__init__(CacheKind.ARTIFACT, max_entries)


def fact_cache_key(
    artifact_fingerprint: str, extractor_version: str, rule_catalog_hash: str
) -> CacheKey:
    return CacheKey(CacheKind.FACT, 1, (artifact_fingerprint, extractor_version, rule_catalog_hash))


def decision_cache_key(
    contract_sha256: str,
    state_fingerprint: str,
    policy_version: str = "kernel-v1",
    calibration_version: str = "none",
) -> CacheKey:
    return CacheKey(
        CacheKind.DECISION,
        1,
        (contract_sha256, state_fingerprint, policy_version, calibration_version),
    )


def artifact_cache_key(
    artifact_kind: str, source_signature: str, compiler_version: str
) -> CacheKey:
    return CacheKey(CacheKind.ARTIFACT, 1, (artifact_kind, source_signature, compiler_version))


class DecisionCache:
    def __init__(self, max_entries: int = 128) -> None:
        if isinstance(max_entries, bool) or max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._items: OrderedDict[str, DecisionResult] = OrderedDict()
        self._metadata: dict[str, CacheRecord] = {}
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.invalidations = 0
        self.last_invalidation_reason: str | None = None

    def get(self, fingerprint: str) -> DecisionResult | None:
        value = self._items.get(fingerprint)
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        self._items.move_to_end(fingerprint)
        return value

    def get_owned(
        self,
        fingerprint: str,
        *,
        owner: str = "decision-kernel",
        freshness: str = "fresh",
    ) -> DecisionResult | None:
        if not owner.strip():
            raise ValueError("cache owner is required")
        result = self.get(fingerprint)
        if result is None:
            return None
        metadata = self._metadata.get(fingerprint)
        if metadata is None or metadata.owner != owner or metadata.freshness != freshness:
            self.invalidate(fingerprint, reason="owner_or_freshness_mismatch")
            return None
        return result

    def put(
        self,
        fingerprint: str,
        result: DecisionResult,
        *,
        owner: str = "decision-kernel",
        freshness: str = "fresh",
    ) -> None:
        if not owner.strip():
            raise ValueError("cache owner is required")
        self._items[fingerprint] = result.with_cache_hit(False)
        key = CacheKey(CacheKind.DECISION, 1, (fingerprint,))
        self._metadata[fingerprint] = CacheRecord(key, result, owner, freshness)
        self._items.move_to_end(fingerprint)
        while len(self._items) > self.max_entries:
            evicted, _ = self._items.popitem(last=False)
            self._metadata.pop(evicted, None)
            self.evictions += 1

    def invalidate(self, fingerprint: str | None = None, *, reason: str = "explicit") -> None:
        if not reason.strip():
            raise ValueError("cache invalidation reason is required")
        self.invalidations += 1
        self.last_invalidation_reason = reason
        if fingerprint is None:
            self._items.clear()
            self._metadata.clear()
        else:
            self._items.pop(fingerprint, None)
            self._metadata.pop(fingerprint, None)

    def clear(self) -> None:
        self.invalidate()

    def __len__(self) -> int:
        return len(self._items)

    def stats(self) -> dict[str, int | str]:
        return {
            "cache_kind": CacheKind.DECISION.value,
            "entries": len(self._items),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "last_invalidation_reason": self.last_invalidation_reason,
        }

    def get_key(self, key: CacheKey) -> DecisionResult | None:
        if key.kind is not CacheKind.DECISION:
            raise ValueError("cache namespace mismatch: expected decision")
        return self.get(key.canonical())

    def put_key(
        self,
        key: CacheKey,
        result: DecisionResult,
        *,
        owner: str = "decision-kernel",
        freshness: str = "fresh",
    ) -> None:
        if key.kind is not CacheKind.DECISION:
            raise ValueError("cache namespace mismatch: expected decision")
        self.put(key.canonical(), result, owner=owner, freshness=freshness)

    def get_key_owned(
        self,
        key: CacheKey,
        *,
        owner: str = "decision-kernel",
        freshness: str = "fresh",
    ) -> DecisionResult | None:
        if key.kind is not CacheKind.DECISION:
            raise ValueError("cache namespace mismatch: expected decision")
        return self.get_owned(key.canonical(), owner=owner, freshness=freshness)


__all__ = [
    "ArtifactCache",
    "CacheKey",
    "CacheKind",
    "CacheRecord",
    "DecisionCache",
    "FactCache",
    "artifact_cache_key",
    "decision_cache_key",
    "fact_cache_key",
]
