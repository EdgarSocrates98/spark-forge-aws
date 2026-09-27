"""Deterministic, versioned expansion of engineering-domain search queries."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_VOCABULARY = Path(__file__).with_name("domain_terms.yaml")


@dataclass(frozen=True, slots=True)
class QueryExpansion:
    query: str
    terms: tuple[str, ...]
    clusters: tuple[str, ...]
    vocabulary_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "query": self.query,
            "terms": list(self.terms),
            "clusters": list(self.clusters),
            "vocabulary_version": self.vocabulary_version,
        }


def expand_query(
    query: str,
    vocabulary: str | Path = DEFAULT_VOCABULARY,
    *,
    max_terms: int = 32,
) -> QueryExpansion:
    if not isinstance(query, str) or not query.strip():
        return QueryExpansion(str(query), (), (), _load(vocabulary).get("version", ""))
    raw = _load(vocabulary)
    stopwords = {_normalize(str(item)) for item in raw.get("stopwords", [])}
    tokens = tuple(
        token
        for token in (_normalize(item) for item in re.findall(r"[\w-]+", query))
        if token and token not in stopwords
    )
    selected: list[dict[str, Any]] = []
    for cluster in raw.get("clusters", []):
        if not isinstance(cluster, dict):
            continue
        triggers = {_normalize(str(item)) for item in cluster.get("gatilhos", [])}
        if triggers.intersection(tokens):
            selected.append(cluster)
    terms = list(dict.fromkeys(tokens))
    for cluster in selected:
        terms.extend(_normalize(str(item)) for item in cluster.get("termos", []))
    terms = list(dict.fromkeys(term for term in terms if term))[: max(0, max_terms)]
    clusters = tuple(str(cluster.get("id", "")) for cluster in selected if cluster.get("id"))
    return QueryExpansion(query.strip(), tuple(terms), clusters, str(raw.get("version", "")))


def _load(path: str | Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"query vocabulary unavailable: {path}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("clusters"), list):
        raise ValueError("query vocabulary must declare clusters")
    return raw


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char)).replace("-", "")


__all__ = ["DEFAULT_VOCABULARY", "QueryExpansion", "expand_query"]
