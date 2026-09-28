"""Bounded caches with explicit namespaces and ownership metadata."""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
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
    def __init__(
        self,
        max_entries: int | Path | str = 128,
        cache_dir: Path | str | None = None,
        default_ttl_seconds: int = 86400,
    ) -> None:
        if isinstance(max_entries, (Path, str)):
            cache_dir = max_entries
            max_entries = 128
        if isinstance(default_ttl_seconds, bool) or default_ttl_seconds < 0:
            raise ValueError("default_ttl_seconds must be non-negative")
        super().__init__(CacheKind.ARTIFACT, max_entries)
        self.cache_dir = (
            Path(cache_dir).expanduser()
            if cache_dir is not None
            else Path.cwd() / ".sparkforge" / "cache"
        )
        self.default_ttl_seconds = default_ttl_seconds

    def get(
        self,
        key_or_namespace: CacheKey | str | None = None,
        inputs: dict[str, Any] | None = None,
        engine_version: str = "0.5.0",
        *,
        namespace: str | None = None,
    ) -> CacheRecord | Any | None:
        if namespace is not None:
            if key_or_namespace is not None and not isinstance(key_or_namespace, CacheKey):
                raise TypeError("provide either namespace or key, not both")
            key_or_namespace = namespace
        if key_or_namespace is None:
            raise TypeError("cache key or namespace is required")
        if isinstance(key_or_namespace, CacheKey):
            return super().get(key_or_namespace)
        key = self._legacy_key(key_or_namespace, inputs or {}, engine_version)
        record = super().get(key)
        if record is not None:
            expires_at = record.value.get("expires_at") if isinstance(record.value, dict) else None
            if expires_at is None or float(expires_at) > time.time():
                return record.value.get("value") if isinstance(record.value, dict) else record.value
            super().invalidate(key, reason="artifact_ttl_expired")
        if self.cache_dir is None:
            return None
        path = self.cache_dir / f"{key.components[1]}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        if not isinstance(data, dict) or float(data.get("expires_at", 0)) <= time.time():
            path.unlink(missing_ok=True)
            return None
        super().put(key, data, owner="economy-facade")
        return data.get("value")

    def set(
        self,
        namespace: str,
        inputs: dict[str, Any],
        value: Any,
        ttl_seconds: int | None = None,
        engine_version: str = "0.5.0",
    ) -> str:
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if isinstance(ttl, bool) or ttl < 0:
            raise ValueError("ttl_seconds must be non-negative")
        key = self._legacy_key(namespace, inputs, engine_version)
        now = time.time()
        data = {
            "key": key.components[1],
            "namespace": namespace,
            "created_at": now,
            "expires_at": now + ttl,
            "value": value,
        }
        super().put(key, data, owner="economy-facade")
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            (self.cache_dir / f"{key.components[1]}.json").write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
            self._trim_disk()
        return key.components[1]

    def clear(self) -> None:
        super().invalidate(reason="explicit_clear")
        if self.cache_dir is not None and self.cache_dir.is_dir():
            for path in self.cache_dir.glob("*.json"):
                path.unlink(missing_ok=True)

    @staticmethod
    def _legacy_key(namespace: str, inputs: dict[str, Any], engine_version: str) -> CacheKey:
        serialized = json.dumps(
            {"ns": namespace, "in": inputs, "v": engine_version},
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return artifact_cache_key(namespace, fingerprint, engine_version)

    def _trim_disk(self) -> None:
        if self.cache_dir is None:
            return
        paths = sorted(self.cache_dir.glob("*.json"), key=lambda path: path.stat().st_mtime)
        for path in paths[: max(0, len(paths) - self.max_entries)]:
            path.unlink(missing_ok=True)


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
        2,
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
        self._metadata[key.canonical()] = CacheRecord(key, result, owner, freshness)

    def limit_to(self, max_entries: int) -> None:
        if isinstance(max_entries, bool) or max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = min(self.max_entries, max_entries)
        while len(self._items) > self.max_entries:
            evicted, _ = self._items.popitem(last=False)
            self._metadata.pop(evicted, None)
            self.evictions += 1

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
