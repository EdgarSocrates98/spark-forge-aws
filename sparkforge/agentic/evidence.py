"""Evidence Engine — classificação e verificação de evidência.

A hierarquia de autoridade (T1-T6) determina o peso da evidência em
arbitragem. Evidência T5 (LLM) e T6 (conjectura) nunca são suficientes
sozinhas para confirmar uma claim de alta confiança.

Esta engine:
1. Classifica fontes em tiers de autoridade.
2. Verifica freshness (vigência vs versão alvo).
3. Verifica scope (aplicabilidade ao runtime alvo).
4. Detecta conflitos entre evidências.
5. Calcula força agregada de um conjunto de evidências.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sparkforge.agentic.models import Evidence, EvidenceAuthority


# Peso numérico por tier — usado em aggregate_strength, não como nota absoluta.
# T1 > T2 > T3 > T4 >> T5 > T6 (T5/T6 não confirmam sozinhos).
_TIER_WEIGHT: dict[EvidenceAuthority, float] = {
    EvidenceAuthority.T1_OFFICIAL_DOCS: 1.0,
    EvidenceAuthority.T2_SOURCE_CODE: 0.9,
    EvidenceAuthority.T3_REPRODUCIBLE_BENCHMARK: 0.85,
    EvidenceAuthority.T4_RECOGNIZED_AUTHORITY: 0.7,
    EvidenceAuthority.T5_LLM_KNOWLEDGE: 0.2,
    EvidenceAuthority.T6_CONJECTURE: 0.1,
}


@dataclass
class EvidenceVerification:
    """Resultado da verificação de uma evidência."""

    evidence_id: str
    is_fresh: bool
    in_scope: bool
    authority: EvidenceAuthority
    weight: float
    issues: list[str] = field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        """Evidência é usável se fresca e em scope."""
        return self.is_fresh and self.in_scope


@dataclass
class AggregateStrength:
    """Força agregada de um conjunto de evidências.

    `sufficient_for_high_confidence` requer pelo menos uma evidência T1-T4
    que seja fresca e em scope. T5/T6 sozinhas nunca são suficientes.
    """

    total_weight: float
    max_tier: EvidenceAuthority
    has_sufficient_authority: bool
    has_fresh_in_scope: bool
    conflict_detected: bool
    evidence_count: int
    sufficient_for_high_confidence: bool


def classify_source(source: str) -> EvidenceAuthority:
    """Classifica uma fonte em tier de autoridade por heurística de URL/path.

    Esta classificação é um ponto de partida — o caller pode override
    quando tem informação adicional (ex: benchmark reproduzido = T3).
    """
    s = source.lower().strip()

    # T2 — código-fonte / release notes / changelog (check antes de T1
    # porque github.com/apache/...releases é release notes, não docs)
    source_indicators = (
        "release-notes",
        "changelog",
        "releases/tag",
        "blob/main",
        "blob/master",
        "blob/branch",
        "tree/main",
        "raw.githubusercontent",
        "/src/",
        ".py:",
        ".scala:",
        ".java:",
    )
    if any(d in s for d in source_indicators):
        return EvidenceAuthority.T2_SOURCE_CODE

    # T1 — documentação oficial (apache.org, docs.aws.amazon.com, etc.)
    # github.com/apache sem path de release notes/source é a org page,
    # não docs — trata como T4 (autoridade reconhecida) se cair aqui.
    official_domains = (
        "apache.org",
        "aws.amazon.com",
        "docs.aws.amazon.com",
        "iceberg.apache.org",
        "spark.apache.org",
        "hadoop.apache.org",
        "docs.iceberg.apache.org",
    )
    if any(d in s for d in official_domains):
        return EvidenceAuthority.T1_OFFICIAL_DOCS

    # T5 — conhecimento LLM (heurística: menciona modelo)
    llm_indicators = ("gpt-", "claude-", "gemini-", "llm says", "ai says", "model output")
    if any(d in s for d in llm_indicators):
        return EvidenceAuthority.T5_LLM_KNOWLEDGE

    # T6 — conjectura / opinião
    conjecture_indicators = ("i think", "probably", "maybe", "i guess", "opinion")
    if any(d in s for d in conjecture_indicators):
        return EvidenceAuthority.T6_CONJECTURE

    # Default: T4 (autoridade reconhecida) para blogs técnicos, papers, etc.
    # Conservador: não assume T1 sem domínio oficial confirmado.
    return EvidenceAuthority.T4_RECOGNIZED_AUTHORITY


def verify_evidence(
    evidence: Evidence,
    target_runtime: dict[str, Any] | None = None,
    target_version: str | None = None,
) -> EvidenceVerification:
    """Verifica freshness e scope de uma evidência.

    Args:
        evidence: A evidência a verificar.
        target_runtime: Runtime alvo (ex: {"spark": "3.5", "iceberg": "1.5"}).
        target_version: Versão alvo específica do componente.

    Returns:
        EvidenceVerification com is_fresh, in_scope, weight, issues.
    """
    issues: list[str] = []

    # Freshness: se a evidência declara version e o target declara version,
    # verifica compatibilidade. Sem version, assume fresh (conservador).
    is_fresh = True
    if evidence.version and target_version:
        if evidence.version != target_version:
            is_fresh = False
            issues.append(
                f"version mismatch: evidence={evidence.version}, target={target_version}"
            )

    # Scope: se a evidência declara scope e o target_runtime tem componentes,
    # verifica sobreposição. Sem scope, assume in_scope.
    in_scope = True
    if evidence.scope and target_runtime:
        scope_lower = evidence.scope.lower()
        runtime_keys = {k.lower() for k in target_runtime}
        # Scope pode ser "spark", "iceberg", "glue", etc.
        if not any(k in scope_lower for k in runtime_keys):
            in_scope = False
            issues.append(
                f"scope mismatch: evidence scope='{evidence.scope}', "
                f"runtime keys={sorted(runtime_keys)}"
            )

    weight = _TIER_WEIGHT.get(evidence.authority, 0.0)

    return EvidenceVerification(
        evidence_id=evidence.id,
        is_fresh=is_fresh,
        in_scope=in_scope,
        authority=evidence.authority,
        weight=weight,
        issues=issues,
    )


def aggregate_strength(
    evidences: list[Evidence],
    target_runtime: dict[str, Any] | None = None,
) -> AggregateStrength:
    """Calcula força agregada de um conjunto de evidências.

    Lógica:
    - has_sufficient_authority: pelo menos uma T1-T4 presente.
    - has_fresh_in_scope: pelo menos uma T1-T4 fresca e em scope.
    - sufficient_for_high_confidence: has_fresh_in_scope AND not conflict.
    - conflict_detected: evidências suportam e contradizem a mesma claim.
    """
    if not evidences:
        return AggregateStrength(
            total_weight=0.0,
            max_tier=EvidenceAuthority.T6_CONJECTURE,
            has_sufficient_authority=False,
            has_fresh_in_scope=False,
            conflict_detected=False,
            evidence_count=0,
            sufficient_for_high_confidence=False,
        )

    verifications = [verify_evidence(e, target_runtime) for e in evidences]
    total_weight = sum(v.weight for v in verifications if v.is_usable)

    # Max tier entre as usáveis
    usable = [v for v in verifications if v.is_usable]
    if usable:
        max_tier = max(usable, key=lambda v: v.weight).authority
    else:
        max_tier = EvidenceAuthority.T6_CONJECTURE

    has_sufficient = any(
        v.authority not in (EvidenceAuthority.T5_LLM_KNOWLEDGE, EvidenceAuthority.T6_CONJECTURE)
        and v.is_usable
        for v in verifications
    )
    has_fresh_in_scope = any(
        v.authority not in (EvidenceAuthority.T5_LLM_KNOWLEDGE, EvidenceAuthority.T6_CONJECTURE)
        and v.is_usable
        for v in verifications
    )

    # Conflito: mesma claim aparece em supports e contradicts
    all_supports: set[str] = set()
    all_contradicts: set[str] = set()
    for e in evidences:
        all_supports.update(e.supports)
        all_contradicts.update(e.contradicts)
    conflict = bool(all_supports & all_contradicts)

    sufficient = has_fresh_in_scope and not conflict

    return AggregateStrength(
        total_weight=total_weight,
        max_tier=max_tier,
        has_sufficient_authority=has_sufficient,
        has_fresh_in_scope=has_fresh_in_scope,
        conflict_detected=conflict,
        evidence_count=len(evidences),
        sufficient_for_high_confidence=sufficient,
    )


def detect_conflicts(evidences: list[Evidence]) -> list[tuple[str, str]]:
    """Detecta pares (claim_id, claim_id) onde evidências conflitam.

    Retorna pares ordenados canonicamente (sorted).
    """
    conflicts: list[tuple[str, str]] = []
    supports_by_claim: dict[str, list[str]] = {}
    contradicts_by_claim: dict[str, list[str]] = {}

    for e in evidences:
        for claim_id in e.supports:
            supports_by_claim.setdefault(claim_id, []).append(e.id)
        for claim_id in e.contradicts:
            contradicts_by_claim.setdefault(claim_id, []).append(e.id)

    # Claim suportada por uma evidência e contraditada por outra
    for claim_id in supports_by_claim:
        if claim_id in contradicts_by_claim:
            for ev_sup in supports_by_claim[claim_id]:
                for ev_con in contradicts_by_claim[claim_id]:
                    if ev_sup != ev_con:
                        conflicts.append((ev_sup, ev_con))

    return conflicts
