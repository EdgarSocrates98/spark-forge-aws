"""Content-addressed, authorized expansion refs backed by ArtifactCache."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sparkforge_aws.context.gateway_budget import content_digest
from sparkforge_aws.context.gateway_models import ContextRef
from sparkforge_aws.economy.cache import ArtifactCache
from sparkforge_aws.paths import resolve_within

_REF_RE = re.compile(r"^ctx://v(?P<version>[1-9][0-9]*)/(?P<kind>[a-z0-9_-]+)/(?P<sha>[0-9a-f]{64})$")


class ContextRefError(ValueError):
    """Named failure for invalid, missing, stale or unauthorized refs."""


class ContextRefStore:
    def __init__(
        self, cache: ArtifactCache | None = None, authorized_root: Path | None = None
    ) -> None:
        self.cache = cache or ArtifactCache()
        self.authorized_root = authorized_root.resolve() if authorized_root is not None else None

    @staticmethod
    def _address(kind: str, payload: Mapping[str, Any], schema_version: int) -> str:
        digest = content_digest(
            {"kind": kind, "schema_version": schema_version, "payload": payload}
        )
        return f"ctx://v{schema_version}/{kind}/{digest}"

    def put(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> ContextRef:
        if not re.fullmatch(r"[a-z0-9_-]+", kind):
            raise ContextRefError("invalid context ref kind")
        schema_version = 1
        uri = self._address(kind, payload, schema_version)
        ref = ContextRef(
            uri=uri,
            kind=kind,
            sha256=uri.rsplit("/", 1)[-1],
            schema_version=schema_version,
        )
        value = {
            "ref": ref.to_dict(),
            "payload": dict(payload),
            "provenance": dict(provenance or {}),
        }
        self.cache.set("context_ref", {"uri": uri}, value)
        return ref

    def resolve(self, uri: str) -> dict[str, Any]:
        match = _REF_RE.fullmatch(uri)
        if match is None:
            raise ContextRefError("invalid context ref")
        value = self.cache.get("context_ref", {"uri": uri})
        if not isinstance(value, Mapping):
            raise ContextRefError("context ref not found or expired")
        payload = value.get("payload")
        if not isinstance(payload, Mapping):
            raise ContextRefError("context ref payload invalid")
        expected = self._address(match.group("kind"), payload, int(match.group("version")))
        if expected != uri:
            raise ContextRefError("context ref integrity check failed")
        source = payload.get("source_path")
        if source is not None and self.authorized_root is not None:
            candidate = self.authorized_root / str(source)
            if candidate.is_symlink():
                raise ContextRefError("context ref source symlink is not allowed")
            if resolve_within(self.authorized_root, candidate) is None:
                raise ContextRefError("context ref source outside authorized scope")
        return dict(value)
