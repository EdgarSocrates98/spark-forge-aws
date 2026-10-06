"""Compile local Markdown/YAML/JSON knowledge into deterministic claim records."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class CompiledClaim:
    claim_id: str
    domain: str
    source: str
    source_hash: str
    authority: str
    version: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {
            "claim_id": self.claim_id,
            "domain": self.domain,
            "source": self.source,
            "source_hash": self.source_hash,
            "authority": self.authority,
            "version": self.version,
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class KnowledgeIndex:
    schema_version: int
    root: str
    claims: tuple[CompiledClaim, ...]
    source_manifest: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root": self.root,
            "claims": [claim.to_dict() for claim in self.claims],
            "source_manifest": [
                {"source": source, "source_hash": source_hash}
                for source, source_hash in self.source_manifest
            ],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> KnowledgeIndex:
        claims = tuple(
            CompiledClaim(
                claim_id=str(item["claim_id"]),
                domain=str(item["domain"]),
                source=str(item["source"]),
                source_hash=str(item["source_hash"]),
                authority=str(item["authority"]),
                version=str(item["version"]),
                text=str(item["text"]),
            )
            for item in raw.get("claims", [])
            if isinstance(item, dict)
        )
        source_manifest = tuple(
            (str(item["source"]), str(item["source_hash"]))
            for item in raw.get("source_manifest", [])
            if isinstance(item, dict) and "source" in item and "source_hash" in item
        )
        return cls(
            int(raw.get("schema_version", 1)),
            str(raw.get("root", "")),
            claims,
            source_manifest,
        )

    def search(self, terms: tuple[str, ...], limit: int = 8) -> tuple[CompiledClaim, ...]:
        normalized = tuple(term.casefold() for term in terms if term)
        ranked = []
        for claim in self.claims:
            haystack = f"{claim.domain} {claim.text}".casefold()
            score = sum(term in haystack for term in normalized)
            if score:
                ranked.append((score, claim.domain, claim.source, claim.claim_id, claim))
        ranked.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))
        return tuple(item[-1] for item in ranked[: max(0, limit)])


def compile_knowledge(
    root: str | Path,
    output: str | Path | None = None,
    *,
    authority: str = "local-unverified",
    version: str = "local",
) -> KnowledgeIndex:
    """Compile supported source files with stable IDs and optional JSON output."""

    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise ValueError(f"knowledge root is not a directory: {base}")
    claims: list[CompiledClaim] = []
    supported = {".md", ".yaml", ".yml", ".json"}
    target = Path(output).expanduser().resolve() if output is not None else None
    source_contents: dict[str, tuple[Path, str, str]] = {}
    for source in _source_files(base, supported):
        if target is not None and source.resolve() == target:
            continue
        if any(part.startswith(".") for part in source.relative_to(base).parts):
            continue
        content = source.read_text(encoding="utf-8", errors="strict")
        source_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        relative = source.relative_to(base).as_posix()
        source_contents[relative] = (source, content, source_hash)
    source_manifest = tuple(
        (relative, values[2]) for relative, values in sorted(source_contents.items())
    )
    if target is not None:
        cached = _load_cached(target, base, source_manifest)
        if cached is not None:
            return cached
    for relative, (source, content, source_hash) in source_contents.items():
        domain = relative.split("/", 1)[0].rsplit(".", 1)[0]
        for ordinal, text in enumerate(_claims(content, source.suffix.lower()), start=1):
            claim_id = hashlib.sha256(
                f"{relative}\n{source_hash}\n{ordinal}\n{text}".encode()
            ).hexdigest()
            claims.append(
                CompiledClaim(
                    claim_id=claim_id,
                    domain=domain,
                    source=relative,
                    source_hash=source_hash,
                    authority=authority,
                    version=version,
                    text=text,
                )
            )
    index = KnowledgeIndex(1, base.as_posix(), tuple(claims), source_manifest)
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(index.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return index


def _load_cached(
    target: Path,
    root: Path,
    source_manifest: tuple[tuple[str, str], ...],
) -> KnowledgeIndex | None:
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    cached = KnowledgeIndex.from_dict(raw)
    if cached.root != root.as_posix() or cached.source_manifest != source_manifest:
        return None
    return cached


def _source_files(root: Path, supported: set[str]) -> tuple[Path, ...]:
    files: list[Path] = []
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        directories[:] = sorted(name for name in directories if not name.startswith("."))
        for name in sorted(names):
            source = Path(current) / name
            if not name.startswith(".") and source.suffix.lower() in supported:
                files.append(source)
    return tuple(files)


def _claims(content: str, suffix: str) -> tuple[str, ...]:
    if suffix == ".md":
        values = [line.strip(" -*\t") for line in content.splitlines()]
        return tuple(line for line in values if line and not line.startswith("#"))
    try:
        value = json.loads(content) if suffix == ".json" else yaml.safe_load(content)
    except (json.JSONDecodeError, yaml.YAMLError):
        return ()
    return tuple(_leaf_strings(value))


def _leaf_strings(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [" ".join(value.split())]
    if isinstance(value, dict):
        result: list[str] = []
        for key in sorted(value):
            result.extend(_leaf_strings(value[key]))
        return result
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_leaf_strings(item))
        return result
    return []


__all__ = ["CompiledClaim", "KnowledgeIndex", "compile_knowledge"]
