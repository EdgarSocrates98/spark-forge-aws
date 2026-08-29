"""Multi-Tier Content-Hash Cache for SparkForge Economy Engine."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class ArtifactCache:
    """Deterministic Cache keyed by content hash and execution inputs."""

    def __init__(self, cache_dir: Path | None = None, default_ttl_seconds: int = 86400) -> None:
        self.cache_dir = cache_dir or (Path.cwd() / ".sparkforge" / "cache")
        self.default_ttl = default_ttl_seconds
        self._memory_cache: dict[str, dict[str, Any]] = {}

    def _compute_key(
        self, namespace: str, inputs: dict[str, Any], engine_version: str = "0.5.0"
    ) -> str:
        serialized = json.dumps(
            {"ns": namespace, "in": inputs, "v": engine_version}, sort_keys=True, default=str
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(
        self, namespace: str, inputs: dict[str, Any], engine_version: str = "0.5.0"
    ) -> Any | None:
        key = self._compute_key(namespace, inputs, engine_version)
        now = time.time()

        # Check memory
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry["expires_at"] > now:
                return entry["value"]
            else:
                del self._memory_cache[key]

        # Check disk
        if self.cache_dir.is_dir():
            file_path = self.cache_dir / f"{key}.json"
            if file_path.is_file():
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    if data.get("expires_at", 0) > now:
                        self._memory_cache[key] = data
                        return data.get("value")
                    else:
                        file_path.unlink(missing_ok=True)
                except Exception:  # noqa: S110 -- entrada ilegivel e cache miss, estado normal
                    pass
        return None

    def set(
        self,
        namespace: str,
        inputs: dict[str, Any],
        value: Any,
        ttl_seconds: int | None = None,
        engine_version: str = "0.5.0",
    ) -> str:
        key = self._compute_key(namespace, inputs, engine_version)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = time.time()
        entry = {
            "key": key,
            "namespace": namespace,
            "created_at": now,
            "expires_at": now + ttl,
            "value": value,
        }
        self._memory_cache[key] = entry

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.cache_dir / f"{key}.json"
            file_path.write_text(json.dumps(entry, indent=2, default=str), encoding="utf-8")
        except Exception:  # noqa: S110 -- cache em disco e best-effort; a memoria ja guardou
            pass

        return key

    def clear(self) -> None:
        self._memory_cache.clear()
        if self.cache_dir.is_dir():
            for f in self.cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
