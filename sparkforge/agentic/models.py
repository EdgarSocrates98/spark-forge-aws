"""Entidades de primeira classe do ciclo agêntico.

Cada entidade é um dataclass frozen com id determinístico, validação em
``__post_init__`` e serialização JSON. O id é content-addressed (sha1 do
payload canônico), como em ``sparkforge.findings.models.Fact`` — a mesma
observação produz sempre o mesmo id entre execuções.

Estas entidades **não substituem** ``Fact``/``Finding``. Elas operam acima:
``Fact`` é observação crua, ``Finding`` é juízo determinístico de regra, e
``Claim``/``Hypothesis``/``Decision`` são juízos agênticos que referenciam
``Fact`` e ``Finding`` por id quando disponíveis.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ClaimType(str, Enum):
    """Tipo de claim. Determina como ela é contestada."""

    OBSERVATION = "observation"  # fato direto, baixa contestação
    INFERENCE = "inference"  # derivado de fatos, contestável
    HYPOTHESIS = "hypothesis"  # explicação propostas, falsificável
    RECOMMENDATION = "recommendation"  # ação proposta, alta contestação


class EvidenceAuthority(str, Enum):
    """Hierarquia de autoridade da fonte. T1 é mais forte, T6 é mais fraco.

    T1 — Documentação oficial vigente (Apache Spark docs, AWS docs, Iceberg spec)
    T2 — Código-fonte / release notes / changelog da versão alvo
    T3 — Benchmark reproduzível em ambiente controlado
    T4 — Postagem técnica de autoridade reconhecida (committers, engenheiros do projeto)
    T5 — Conhecimento LLM sem citação verificável
    T6 — Conjectura / opinião sem fonte

    Conhecimento LLM (T5) nunca é suficiente sozinho para confirmar uma claim.
    """

    T1_OFFICIAL_DOCS = "T1"
    T2_SOURCE_CODE = "T2"
    T3_REPRODUCIBLE_BENCHMARK = "T3"
    T4_RECOGNIZED_AUTHORITY = "T4"
    T5_LLM_KNOWLEDGE = "T5"
    T6_CONJECTURE = "T6"


class HypothesisStatus(str, Enum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    ABANDONED = "abandoned"


class UnknownStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"  # não resolúvel, aceito como incerteza


class ExperimentStatus(str, Enum):
    PROPOSED = "proposed"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABANDONED = "abandoned"


CONFIDENCE_VALUES = frozenset({"high", "medium", "low"})


def _canonical(value: Any) -> str:
    """JSON canônico: chaves ordenadas, sem espaços. Base do id estável."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(prefix: str, payload: dict[str, Any]) -> str:
    """sha1[:8] do payload canônico, prefixado para legibilidade.

    sha1 aqui é content-addressing, não uso criptográfico: identifica o que a
    entidade afirma para que a mesma afirmação produza o mesmo id entre runs.
    """
    raw = _canonical(payload).encode("utf-8")
    h = hashlib.sha1(raw, usedforsecurity=False).hexdigest()
    return f"{prefix}_{h[:8]}"


# ======================================================================
# Claim — afirmação feita por um agente
# ======================================================================


@dataclass(frozen=True)
class Claim:
    """Afirmação feita por um agente durante a investigação.

    Toda claim é falsificável (ou declara não ser) e carrega evidência
    referenciada por id (fact_id, evidence_id ou finding rule_id).
    """

    claimant: str  # agent_id
    claim_type: ClaimType
    statement: str
    evidence_refs: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    confidence: str = "low"  # high/medium/low — declarada, não confiável
    falsifiable: bool = True
    created_at: str = ""  # ISO 8601, injetado pelo caller

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("Claim: statement vazio.")
        if self.confidence not in CONFIDENCE_VALUES:
            raise ValueError(
                f"Claim: confidence {self.confidence!r} inválida "
                f"(esperado: {', '.join(sorted(CONFIDENCE_VALUES))})"
            )
        if not isinstance(self.claim_type, ClaimType):
            raise ValueError(
                f"Claim: claim_type deve ser ClaimType, recebido {type(self.claim_type)}"
            )

    @property
    def id(self) -> str:
        payload = {
            "claimant": self.claimant,
            "claim_type": self.claim_type.value,
            "statement": self.statement,
        }
        return _digest("claim", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claimant": self.claimant,
            "claim_type": self.claim_type.value,
            "statement": self.statement,
            "evidence_refs": list(self.evidence_refs),
            "assumptions": list(self.assumptions),
            "confidence": self.confidence,
            "falsifiable": self.falsifiable,
            "created_at": self.created_at,
        }


# ======================================================================
# Evidence — evidência classificada por autoridade
# ======================================================================


@dataclass(frozen=True)
class Evidence:
    """Evidência classificada por autoridade da fonte.

    A autoridade determina peso em arbitragem. T5 (LLM) e T6 (conjectura)
    nunca são suficientes sozinhos para confirmar uma claim de alta confiança.
    """

    source: str  # fact_id, url, doc path, finding rule_id
    authority: EvidenceAuthority
    freshness: str = ""  # ISO date ou versão
    version: str | None = None
    scope: str = ""  # a que versão/runtime esta evidência se aplica
    applicability: str = ""  # condições de aplicabilidade
    supports: list[str] = field(default_factory=list)  # claim_ids
    contradicts: list[str] = field(default_factory=list)  # claim_ids

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("Evidence: source vazio.")
        if not isinstance(self.authority, EvidenceAuthority):
            raise ValueError(
                f"Evidence: authority deve ser EvidenceAuthority, recebido {type(self.authority)}"
            )

    @property
    def id(self) -> str:
        payload = {
            "source": self.source,
            "authority": self.authority.value,
            "scope": self.scope,
        }
        return _digest("ev", payload)

    @property
    def is_sufficient_alone(self) -> bool:
        """T5/T6 não são suficientes sozinhos para confirmar uma claim."""
        return self.authority not in (
            EvidenceAuthority.T5_LLM_KNOWLEDGE,
            EvidenceAuthority.T6_CONJECTURE,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "authority": self.authority.value,
            "freshness": self.freshness,
            "version": self.version,
            "scope": self.scope,
            "applicability": self.applicability,
            "supports": list(self.supports),
            "contradicts": list(self.contradicts),
        }


# ======================================================================
# Hypothesis — explicação proposta, falsificável
# ======================================================================


@dataclass(frozen=True)
class Hypothesis:
    """Hipótese: explicação proposta para um fenômeno observado.

    Toda hipótese declara:
    - expected_outcome: o que esperamos ver se a hipótese é verdadeira
    - failure_modes: como ela pode estar errada
    - falsification_method: como refutá-la
    """

    statement: str
    supporting_evidence: list[str] = field(default_factory=list)  # evidence_ids
    contradicting_evidence: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    failure_modes: list[str] = field(default_factory=list)
    confidence: str = "low"
    falsification_method: str = ""
    status: HypothesisStatus = HypothesisStatus.OPEN
    proposed_by: str = ""  # agent_id

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("Hypothesis: statement vazio.")
        if self.confidence not in CONFIDENCE_VALUES:
            raise ValueError(f"Hypothesis: confidence {self.confidence!r} inválida")
        if not isinstance(self.status, HypothesisStatus):
            raise ValueError("Hypothesis: status deve ser HypothesisStatus")

    @property
    def id(self) -> str:
        payload = {
            "statement": self.statement,
            "proposed_by": self.proposed_by,
        }
        return _digest("hyp", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "supporting_evidence": list(self.supporting_evidence),
            "contradicting_evidence": list(self.contradicting_evidence),
            "assumptions": list(self.assumptions),
            "expected_outcome": self.expected_outcome,
            "failure_modes": list(self.failure_modes),
            "confidence": self.confidence,
            "falsification_method": self.falsification_method,
            "status": self.status.value,
            "proposed_by": self.proposed_by,
        }


# ======================================================================
# Experiment — teste de hipótese com variável controlada
# ======================================================================


@dataclass(frozen=True)
class Experiment:
    """Experimento para resolver desacordo ou validar hipótese.

    Uma variável mudada por experimento. Baseline e controls explícitos.
    Success e failure criteria machine-checkable quando possível.
    """

    hypothesis_id: str
    variable: str  # única variável alterada
    baseline: str  # estado antes do experimento
    controls: list[str] = field(default_factory=list)  # variáveis mantidas
    expected_results: str = ""
    success_criteria: str = ""
    failure_criteria: str = ""
    rollback: str = ""
    cost_estimate: str = ""
    time_estimate: str = ""
    status: ExperimentStatus = ExperimentStatus.PROPOSED
    result: str | None = None
    proposed_by: str = ""

    def __post_init__(self) -> None:
        if not self.hypothesis_id.strip():
            raise ValueError("Experiment: hypothesis_id vazio.")
        if not self.variable.strip():
            raise ValueError("Experiment: variable vazio — uma variável por experimento.")
        if not isinstance(self.status, ExperimentStatus):
            raise ValueError("Experiment: status deve ser ExperimentStatus")

    @property
    def id(self) -> str:
        payload = {
            "hypothesis_id": self.hypothesis_id,
            "variable": self.variable,
            "baseline": self.baseline,
        }
        return _digest("exp", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "hypothesis_id": self.hypothesis_id,
            "variable": self.variable,
            "baseline": self.baseline,
            "controls": list(self.controls),
            "expected_results": self.expected_results,
            "success_criteria": self.success_criteria,
            "failure_criteria": self.failure_criteria,
            "rollback": self.rollback,
            "cost_estimate": self.cost_estimate,
            "time_estimate": self.time_estimate,
            "status": self.status.value,
            "result": self.result,
            "proposed_by": self.proposed_by,
        }


# ======================================================================
# Decision — decisão auditável com rollback
# ======================================================================


@dataclass(frozen=True)
class Decision:
    """Decisão final auditável.

    Toda decisão registra:
    - options consideradas (não apenas a selecionada)
    - evidence que sustenta a escolha
    - debate que contestou (se houve)
    - experiments que validaram (se houve)
    - risks, assumptions, unknowns
    - validation e rollback
    - falsification_condition: sob que condição esta decisão seria revertida
    """

    problem: str
    options: list[str]
    selected_option: str
    rejected_options: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    debate_id: str | None = None
    experiment_ids: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)  # unknown_ids
    confidence: str = "low"
    runtime: dict[str, Any] = field(default_factory=dict)  # RuntimeContext snapshot
    validation: str = ""
    rollback: str = ""
    falsification_condition: str = ""
    decided_by: str = ""  # agent_id ou "human"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.problem.strip():
            raise ValueError("Decision: problem vazio.")
        if not self.options:
            raise ValueError("Decision: options vazio — registre alternativas.")
        if self.selected_option not in self.options:
            raise ValueError(
                f"Decision: selected_option {self.selected_option!r} não está em options"
            )
        if self.confidence not in CONFIDENCE_VALUES:
            raise ValueError(f"Decision: confidence {self.confidence!r} inválida")
        if not self.rollback.strip():
            raise ValueError(
                "Decision: rollback vazio — toda decisão declara rollback ou "
                "'irreversible: <motivo>'"
            )

    @property
    def id(self) -> str:
        payload = {
            "problem": self.problem,
            "selected_option": self.selected_option,
            "decided_by": self.decided_by,
        }
        return _digest("dec", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "problem": self.problem,
            "options": list(self.options),
            "selected_option": self.selected_option,
            "rejected_options": list(self.rejected_options),
            "evidence_refs": list(self.evidence_refs),
            "debate_id": self.debate_id,
            "experiment_ids": list(self.experiment_ids),
            "risks": list(self.risks),
            "assumptions": list(self.assumptions),
            "unknowns": list(self.unknowns),
            "confidence": self.confidence,
            "runtime": dict(self.runtime),
            "validation": self.validation,
            "rollback": self.rollback,
            "falsification_condition": self.falsification_condition,
            "decided_by": self.decided_by,
            "created_at": self.created_at,
        }


# ======================================================================
# Unknown — incerteza explícita, nunca vira fact por conveniência
# ======================================================================


@dataclass(frozen=True)
class Unknown:
    """Incerteza explícita. Unknown nunca vira fact sem evidência.

    Fluxo proibido: unknown → guess → fact.
    Fluxo correto:  unknown → evidence_needed → experiment → resolved.
    Quando não há evidência, retorna UNRESOLVED, não hallucinated certainty.
    """

    question: str
    impact: str = ""  # que decisão esta incerteza bloqueia ou degrada
    blocking: bool = False
    owner: str | None = None  # agent_id responsável por resolver
    evidence_needed: list[str] = field(default_factory=list)
    resolution_method: str | None = None
    status: UnknownStatus = UnknownStatus.OPEN

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError("Unknown: question vazio.")
        if not isinstance(self.status, UnknownStatus):
            raise ValueError("Unknown: status deve ser UnknownStatus")

    @property
    def id(self) -> str:
        payload = {"question": self.question}
        return _digest("unk", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "impact": self.impact,
            "blocking": self.blocking,
            "owner": self.owner,
            "evidence_needed": list(self.evidence_needed),
            "resolution_method": self.resolution_method,
            "status": self.status.value,
        }


# ======================================================================
# Contradiction — conflito entre claims detectado
# ======================================================================


@dataclass(frozen=True)
class Contradiction:
    """Contradição detectada entre duas claims.

    A resolução pode ser: debate, experiment, arbitration, ou unresolved.
    Contradictions não resolvidas bloqueiam decisões de alta confiança.
    """

    claim_a: str  # claim_id
    claim_b: str  # claim_id
    description: str
    detected_by: str = ""  # agent_id ou "system"
    resolution: str | None = None  # debate/experiment/arbitration/unresolved

    def __post_init__(self) -> None:
        if not self.claim_a or not self.claim_b:
            raise ValueError("Contradiction: claim_a e claim_b obrigatórios.")
        if self.claim_a == self.claim_b:
            raise ValueError("Contradiction: claim_a == claim_b — não é contradição.")
        if not self.description.strip():
            raise ValueError("Contradiction: description vazio.")

    @property
    def id(self) -> str:
        # Ordem canônica: par ordenado independente de ordem de entrada
        pair = sorted([self.claim_a, self.claim_b])
        payload = {"claims": pair, "description": self.description}
        return _digest("ctr", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim_a": self.claim_a,
            "claim_b": self.claim_b,
            "description": self.description,
            "detected_by": self.detected_by,
            "resolution": self.resolution,
        }


# ======================================================================
# Objection — contestação de uma claim
# ======================================================================


@dataclass(frozen=True)
class Objection:
    """Objeção levantada contra uma claim por outro agente.

    A objação deve ter evidência própria — não é apenas discordância.
    """

    target_claim: str  # claim_id
    objector: str  # agent_id
    statement: str
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.target_claim.strip():
            raise ValueError("Objection: target_claim vazio.")
        if not self.objector.strip():
            raise ValueError("Objection: objector vazio.")
        if not self.statement.strip():
            raise ValueError("Objection: statement vazio.")

    @property
    def id(self) -> str:
        payload = {
            "target_claim": self.target_claim,
            "objector": self.objector,
            "statement": self.statement,
        }
        return _digest("obj", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_claim": self.target_claim,
            "objector": self.objector,
            "statement": self.statement,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
        }


# ======================================================================
# Rebuttal — resposta a uma objeção
# ======================================================================


@dataclass(frozen=True)
class Rebuttal:
    """Resposta a uma objeção, com evidência própria."""

    target_objection: str  # objection_id
    rebuttal_by: str  # agent_id
    statement: str
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.target_objection.strip():
            raise ValueError("Rebuttal: target_objection vazio.")
        if not self.rebuttal_by.strip():
            raise ValueError("Rebuttal: rebuttal_by vazio.")
        if not self.statement.strip():
            raise ValueError("Rebuttal: statement vazio.")

    @property
    def id(self) -> str:
        payload = {
            "target_objection": self.target_objection,
            "rebuttal_by": self.rebuttal_by,
            "statement": self.statement,
        }
        return _digest("reb", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_objection": self.target_objection,
            "rebuttal_by": self.rebuttal_by,
            "statement": self.statement,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
        }
