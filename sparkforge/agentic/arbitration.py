"""Arbitration — arbitragem independente e detecção de falso consenso.

Arbitragem não é votação majoritária. O árbitro avalia:
- evidence quality (tier de autoridade)
- source authority (T1 > T2 > ... > T6)
- independence (false consensus detection)
- specificity (evidência específica vs genérica)
- runtime applicability (versão alvo)
- version applicability
- counterexamples (presença refuta claim)
- risk, cost, performance, correctness

False consensus: 5 agentes independentes > 5 agentes derivados do mesmo
contexto. independence_score mede se conclusões são correlacionadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sparkforge.agentic.evidence import aggregate_strength, verify_evidence
from sparkforge.agentic.models import Claim, Evidence, EvidenceAuthority


@dataclass
class ArbitrationResult:
    """Resultado de arbitragem."""

    winning_claim_id: str | None
    reasoning: str
    confidence: str  # high/medium/low
    independence_score: float  # 0.0 a 1.0
    false_consensus_detected: bool
    evidence_quality_winner: float
    evidence_quality_loser: float
    counterexamples_found: list[str] = field(default_factory=list)
    unknowns_remaining: list[str] = field(default_factory=list)
    recommendation: str = ""  # "accept" | "reject" | "experiment" | "escalate"


@dataclass
class ClaimAssessment:
    """Avaliação de uma claim individual pelo árbitro."""

    claim_id: str
    evidence_weight: float
    authority_tier: EvidenceAuthority
    specificity: float  # 0.0 a 1.0 — quão específica é a evidência
    has_counterexample: bool
    runtime_applicable: bool
    version_applicable: bool
    score: float  # weighted aggregate


def assess_claim(
    claim: Claim,
    evidences: list[Evidence],
    target_runtime: dict[str, Any] | None = None,
    target_version: str | None = None,
) -> ClaimAssessment:
    """Avalia uma claim individual pelo árbitro.

    Critérios:
    - evidence_weight: soma dos pesos das evidências usáveis
    - authority_tier: tier da melhor evidência usável
    - specificity: 1.0 se evidência é específica ao runtime, 0.5 se genérica
    - has_counterexample: existe evidência que contradiz
    - runtime_applicable: evidência se aplica ao runtime alvo
    - version_applicable: evidência se aplica à versão alvo
    - score: weighted aggregate (evidence 40%, authority 30%, specificity 20%, applicability 10%)
    """
    strength = aggregate_strength(evidences, target_runtime)

    # Filtra evidências que suportam esta claim
    supporting = [e for e in evidences if claim.id in e.supports]
    contradicting = [e for e in evidences if claim.id in e.contradicts]

    # Verifica each supporting evidence
    usable_supporting: list[Evidence] = []
    for e in supporting:
        v = verify_evidence(e, target_runtime, target_version)
        if v.is_usable:
            usable_supporting.append(e)

    # Best authority among usable supporting
    if usable_supporting:
        best_authority = max(
            (
                verify_evidence(e, target_runtime, target_version).authority
                for e in usable_supporting
            ),
            key=lambda a: _TIER_ORDER.get(a, 0),
        )
    else:
        best_authority = EvidenceAuthority.T6_CONJECTURE

    # Specificity: 1.0 se evidência declara scope matching runtime, 0.5 se genérica
    if target_runtime and any(e.scope for e in usable_supporting):
        runtime_keys = {k.lower() for k in target_runtime}
        scoped = [
            e
            for e in usable_supporting
            if e.scope and any(k in e.scope.lower() for k in runtime_keys)
        ]
        specificity = 1.0 if scoped else 0.5
    else:
        specificity = 0.5 if usable_supporting else 0.0

    has_counterexample = len(contradicting) > 0

    # Runtime/version applicability
    runtime_applicable = (
        all(verify_evidence(e, target_runtime, target_version).in_scope for e in usable_supporting)
        if usable_supporting
        else False
    )
    version_applicable = (
        all(verify_evidence(e, target_runtime, target_version).is_fresh for e in usable_supporting)
        if usable_supporting
        else False
    )

    # Score: weighted aggregate
    evidence_score = min(strength.total_weight / 2.0, 1.0)  # normalize
    if usable_supporting:
        authority_score = _TIER_ORDER.get(best_authority, 0) / 6.0  # 0-1
    else:
        authority_score = 0.0
    specificity_score = specificity
    if usable_supporting:
        applicability_score = 1.0 if (runtime_applicable and version_applicable) else 0.5
    else:
        applicability_score = 0.0

    score = (
        0.40 * evidence_score
        + 0.30 * authority_score
        + 0.20 * specificity_score
        + 0.10 * applicability_score
    )

    # Penalty for counterexamples
    if has_counterexample:
        score *= 0.5

    return ClaimAssessment(
        claim_id=claim.id,
        evidence_weight=strength.total_weight,
        authority_tier=best_authority,
        specificity=specificity,
        has_counterexample=has_counterexample,
        runtime_applicable=runtime_applicable,
        version_applicable=version_applicable,
        score=score,
    )


_TIER_ORDER: dict[EvidenceAuthority, int] = {
    EvidenceAuthority.T6_CONJECTURE: 1,
    EvidenceAuthority.T5_LLM_KNOWLEDGE: 2,
    EvidenceAuthority.T4_RECOGNIZED_AUTHORITY: 3,
    EvidenceAuthority.T3_REPRODUCIBLE_BENCHMARK: 4,
    EvidenceAuthority.T2_SOURCE_CODE: 5,
    EvidenceAuthority.T1_OFFICIAL_DOCS: 6,
}


def compute_independence_score(
    claims: list[Claim],
    evidences: list[Evidence],
) -> float:
    """Computa independence score: 0.0 (correlated) a 1.0 (independent).

    False consensus: agentes que derivam conclusões do mesmo contexto
    produzem claims correlacionadas. Independence mede diversidade de:
    - evidence sources (fontes distintas)
    - claimants (agentes distintos)
    - statement diversity (statements não são paráfrases)

    Heurística simples:
    - claimants únicos / total claims
    - evidence sources únicos / total evidences
    - Média dos dois
    """
    if not claims:
        return 0.0

    unique_claimants = len({c.claimant for c in claims})
    claimant_diversity = unique_claimants / len(claims)

    if evidences:
        unique_sources = len({e.source for e in evidences})
        # Source diversity relative to claims: if 1 source backs N claims,
        # diversity is 1/N, not 1/1.
        source_diversity = unique_sources / max(len(claims), len(evidences))
    else:
        source_diversity = 0.0

    return (claimant_diversity + source_diversity) / 2.0


def detect_false_consensus(
    claims: list[Claim],
    evidences: list[Evidence],
    threshold: float = 0.3,
) -> bool:
    """Detecta falso consenso.

    Falso consenso: múltiplos agentes concordam mas:
    - baixa independence score (< threshold)
    - mesma fonte de evidência
    - mesmos claimants ou claimants derivados

    Retorna True se independence_score < threshold.
    """
    if len(claims) < 2:
        return False

    independence = compute_independence_score(claims, evidences)
    return independence < threshold


def arbitrate(
    claims: list[Claim],
    evidences: list[Evidence],
    target_runtime: dict[str, Any] | None = None,
    target_version: str | None = None,
) -> ArbitrationResult:
    """Arbitra entre claims conflitantes.

    Não é votação majoritária. Avalia cada claim por:
    - evidence quality
    - source authority
    - independence
    - specificity
    - runtime/version applicability
    - counterexamples

    Retorna:
    - winning_claim_id: claim com maior score (ou None se todas baixas)
    - recommendation: accept | reject | experiment | escalate
    """
    if not claims:
        return ArbitrationResult(
            winning_claim_id=None,
            reasoning="No claims to arbitrate.",
            confidence="low",
            independence_score=0.0,
            false_consensus_detected=False,
            evidence_quality_winner=0.0,
            evidence_quality_loser=0.0,
            recommendation="reject",
        )

    # Assess each claim
    assessments = [assess_claim(c, evidences, target_runtime, target_version) for c in claims]

    # Sort by score descending
    assessments.sort(key=lambda a: a.score, reverse=True)

    winner = assessments[0]
    loser = assessments[-1]

    # Independence check
    independence = compute_independence_score(claims, evidences)
    false_consensus = detect_false_consensus(claims, evidences)

    # Counterexamples
    counterexamples = [a.claim_id for a in assessments if a.has_counterexample]

    # Determine recommendation
    if winner.score < 0.3:
        recommendation = "escalate"
        reasoning = (
            f"Best claim score {winner.score:.2f} below threshold. "
            "Insufficient evidence for any claim."
        )
        confidence = "low"
    elif false_consensus:
        recommendation = "experiment"
        reasoning = (
            f"False consensus detected: independence_score={independence:.2f}. "
            f"Claims may be correlated. Experiment needed to resolve."
        )
        confidence = "low"
    elif winner.has_counterexample:
        recommendation = "experiment"
        reasoning = (
            f"Winning claim {winner.claim_id} has counterexample evidence. "
            f"Experiment needed to resolve contradiction."
        )
        confidence = "medium"
    elif winner.score - loser.score < 0.1:
        recommendation = "experiment"
        reasoning = (
            f"Claims are close in score (winner={winner.score:.2f}, "
            f"loser={loser.score:.2f}). Experiment needed to differentiate."
        )
        confidence = "medium"
    else:
        recommendation = "accept"
        reasoning = (
            f"Claim {winner.claim_id} wins with score {winner.score:.2f}. "
            f"Evidence quality sufficient, no counterexamples, "
            f"independence_score={independence:.2f}."
        )
        confidence = "high" if winner.score > 0.7 else "medium"

    return ArbitrationResult(
        winning_claim_id=winner.claim_id,
        reasoning=reasoning,
        confidence=confidence,
        independence_score=independence,
        false_consensus_detected=false_consensus,
        evidence_quality_winner=winner.evidence_weight,
        evidence_quality_loser=loser.evidence_weight,
        counterexamples_found=counterexamples,
        recommendation=recommendation,
    )
