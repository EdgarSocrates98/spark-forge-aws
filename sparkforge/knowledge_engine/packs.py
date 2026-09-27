"""Metadata-first registry for demand-loaded local knowledge packs."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.codeintel.query_expansion import QueryExpansion, expand_query
from sparkforge.knowledge_engine.compiler import KnowledgeIndex, compile_knowledge


@dataclass(frozen=True, slots=True)
class PackDescriptor:
    domain: str
    path: str
    source_hash: str
    files: int


class PackRegistry:
    """Discover pack metadata without loading pack bodies into the caller."""

    def __init__(self, root: str | Path, cache_dir: str | Path | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        self.cache_dir = (
            Path(cache_dir).expanduser().resolve()
            if cache_dir is not None
            else self.root.parent / ".sparkforge-knowledge-cache"
        )
        self._indexes: dict[tuple[str, str], KnowledgeIndex] = {}

    def descriptors(self) -> tuple[PackDescriptor, ...]:
        if not self.root.is_dir():
            return ()
        result = []
        for directory in sorted(item for item in self.root.iterdir() if item.is_dir()):
            files = _pack_files(directory)
            digest = hashlib.sha256()
            for item in files:
                digest.update(item.relative_to(directory).as_posix().encode("utf-8"))
                digest.update(item.read_bytes())
            result.append(
                PackDescriptor(directory.name, directory.as_posix(), digest.hexdigest(), len(files))
            )
        return tuple(result)

    def load(self, domain: str) -> KnowledgeIndex:
        descriptor = next((item for item in self.descriptors() if item.domain == domain), None)
        if descriptor is None:
            raise KeyError(f"knowledge pack not found: {domain}")
        key = (descriptor.domain, descriptor.source_hash)
        cached = self._indexes.get(key)
        if cached is not None:
            return cached
        target = self.cache_dir / f"{descriptor.domain}-{descriptor.source_hash}.json"
        index = compile_knowledge(descriptor.path, output=target)
        self._indexes[key] = index
        return index

    def select(
        self,
        query: str,
        *,
        limit: int = 8,
        expansion: QueryExpansion | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Load only candidate packs, then return bounded matching claims."""
        expanded = expansion or expand_query(query)
        terms = tuple(term.casefold() for term in expanded.terms)
        candidates = [
            item
            for item in self.descriptors()
            if any(term in item.domain.casefold() for term in terms)
        ]
        if not candidates:
            candidates = list(self.descriptors())
        claims: list[dict[str, Any]] = []
        for descriptor in candidates:
            index = self.load(descriptor.domain)
            matches = index.search(terms, limit=limit)
            if not matches and descriptor.domain.casefold() in terms:
                matches = index.claims[:limit]
            claims.extend(item.to_dict() for item in matches)
        claims.sort(key=lambda item: (item["domain"], item["source"], item["claim_id"]))
        return tuple(claims[: max(0, limit)])


def _pack_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        directories[:] = sorted(name for name in directories if name != ".git")
        files.extend(Path(current) / name for name in sorted(names))
    return tuple(files)


__all__ = ["PackDescriptor", "PackRegistry"]
