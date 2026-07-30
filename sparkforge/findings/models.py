"""Contratos de dados: Fact, Finding, RuntimeContext.

Fact é observação crua ancorada, sem juízo. Finding é juízo, sempre lastreado por
pelo menos um Fact. Ordenação é determinística para golden test não flakar.
Ver docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md secao 5.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1
SEVERITY_ORDER: tuple[str, ...] = ("P0", "P1", "P2", "P3", "P4")
CONFIDENCE_VALUES = frozenset({"high", "medium", "low"})
STATUS_VALUES = frozenset({"structural", "confirmed"})


def _canonical(value: Any) -> str:
    """JSON canônico: chaves ordenadas, sem espaços. Base do id estável."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _subject_key(subject: dict[str, Any]) -> str:
    return _canonical(subject)


@dataclass(frozen=True)
class Fact:
    """Observação determinística ancorada. Nunca contém juízo nem limiar."""

    kind: str
    subject: dict[str, Any]
    measures: dict[str, Any] = field(default_factory=dict)
    attrs: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    @property
    def id(self) -> str:
        """sha1[:6] de (kind + subject + measures). Provenance não entra: ela
        registra de onde o fact veio, não o que ele afirma."""
        payload = _canonical(
            {"kind": self.kind, "subject": self.subject, "measures": self.measures}
        )
        # sha1 aqui é digest de content-addressing, não uso criptográfico:
        # identifica o que o fact afirma para que a mesma observação produza
        # o mesmo id entre execuções. Resistência a colisão é irrelevante
        # para esse fim, e o truncamento para 6 hex chars torna a força
        # criptográfica moot de qualquer forma.
        digest = hashlib.sha1(payload.encode("utf-8"), usedforsecurity=False).hexdigest()
        return "f_" + digest[:6]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "schema_version": self.schema_version,
            "kind": self.kind,
            "subject": self.subject,
            "measures": self.measures,
            "attrs": self.attrs,
            "provenance": self.provenance,
        }


@dataclass
class Finding:
    """Juízo sobre o sistema analisado. `evidence` nunca vazio."""

    rule_id: str
    title: str
    severity: str
    confidence: str
    status: str
    subject: dict[str, Any]
    evidence: list[str]
    measured: dict[str, Any] = field(default_factory=dict)
    threshold: dict[str, Any] = field(default_factory=dict)
    runtime_scope: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    proposed_change: list[str] = field(default_factory=list)
    expected_effect: str = ""
    benchmark_ref: str = ""
    risks: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)
    rollback: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    catalog_version: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError(
                f"Finding {self.rule_id}: evidence vazio. Finding sem Fact e invalido."
            )
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(
                f"Finding {self.rule_id}: severity {self.severity!r} desconhecida "
                f"(esperado: {', '.join(SEVERITY_ORDER)})"
            )
        if self.confidence not in CONFIDENCE_VALUES:
            raise ValueError(
                f"Finding {self.rule_id}: confidence {self.confidence!r} desconhecida"
            )
        if self.status not in STATUS_VALUES:
            raise ValueError(
                f"Finding {self.rule_id}: status {self.status!r} desconhecido "
                f"(esperado: {', '.join(sorted(STATUS_VALUES))})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "schema_version": self.schema_version,
            "catalog_version": self.catalog_version,
            "title": self.title,
            "severity": self.severity,
            "confidence": self.confidence,
            "status": self.status,
            "subject": self.subject,
            "evidence": list(self.evidence),
            "measured": self.measured,
            "threshold": self.threshold,
            "runtime_scope": self.runtime_scope,
            "explanation": self.explanation,
            "proposed_change": list(self.proposed_change),
            "expected_effect": self.expected_effect,
            "benchmark_ref": self.benchmark_ref,
            "risks": list(self.risks),
            "tradeoffs": list(self.tradeoffs),
            "validation": list(self.validation),
            "rollback": list(self.rollback),
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class RuntimeContext:
    """Versões detectadas. `divergences` não vazio significa detecção conflitante."""

    glue: str = ""
    spark: str = ""
    python: str = ""
    iceberg: str = ""
    athena: str = ""
    detected_from: Sequence[str] = ()
    divergences: Sequence[str] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "glue": self.glue,
            "spark": self.spark,
            "python": self.python,
            "iceberg": self.iceberg,
            "athena": self.athena,
            "detected_from": list(self.detected_from),
            "divergences": list(self.divergences),
        }


def sort_facts(facts: Iterable[Fact]) -> list[Fact]:
    """Ordem determinística: (kind, subject canônico, id)."""
    return sorted(facts, key=lambda f: (f.kind, _subject_key(f.subject), f.id))


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Ordem determinística: (severidade, rule_id, subject canônico)."""
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_ORDER.index(f.severity),
            f.rule_id,
            _subject_key(f.subject),
        ),
    )
