"""Trust plane primitives for agentic context and cross-agent messages.

Trust is data provenance, not instruction authority. External text may become a
verified fact after deterministic extraction, but it never becomes a system
instruction merely because it was relayed by a tool or another agent.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Any


class TrustLabel(str, Enum):
    SYSTEM = "SYSTEM"
    POLICY = "POLICY"
    VERIFIED_FACT = "VERIFIED_FACT"
    VERIFIED_FINDING = "VERIFIED_FINDING"
    KNOWLEDGE = "KNOWLEDGE"
    MEMORY = "MEMORY"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    USER_INPUT = "USER_INPUT"
    EXTERNAL_DATA = "EXTERNAL_DATA"
    EXTERNAL_UNTRUSTED = "EXTERNAL_UNTRUSTED"
    UNKNOWN = "UNKNOWN"


class InstructionAuthority(str, Enum):
    NONE = "none"
    DATA_ONLY = "data_only"
    POLICY = "policy"
    SYSTEM = "system"


class Taint(str, Enum):
    CLEAN = "clean"
    EXTERNAL = "external"
    SUSPICIOUS = "suspicious"
    POISONED = "poisoned"


# A ordem do enum e ordem de DECLARACAO, nao politica: mover um label para o
# fim da lista nao pode rebaixar um artefato verificado abaixo de dado cru.
# O rank e escrito aqui, explicito, e `RoleContextPlan.allows` so compara ele.
TRUST_RANK: dict[TrustLabel, int] = {
    TrustLabel.SYSTEM: 110,
    TrustLabel.POLICY: 100,
    TrustLabel.VERIFIED_FACT: 90,
    TrustLabel.VERIFIED_FINDING: 80,
    TrustLabel.KNOWLEDGE: 70,
    TrustLabel.MEMORY: 60,
    TrustLabel.TOOL_OUTPUT: 50,
    TrustLabel.MODEL_OUTPUT: 40,
    TrustLabel.USER_INPUT: 30,
    TrustLabel.EXTERNAL_DATA: 20,
    TrustLabel.EXTERNAL_UNTRUSTED: 10,
    TrustLabel.UNKNOWN: 0,
}

_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "system message:",
    "developer message:",
    "you are now",
    "new instructions:",
    "do not tell the user",
)


def _digest(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class TrustEnvelope:
    """A context unit with explicit provenance and non-instruction authority."""

    content: str
    origin: str
    trust: TrustLabel = TrustLabel.UNKNOWN
    scope: str = ""
    instruction_authority: InstructionAuthority = InstructionAuthority.NONE
    taint: Taint = Taint.CLEAN
    provenance: tuple[str, ...] = ()
    freshness: str = "unknown"
    content_kind: str = "data"

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("TrustEnvelope: content vazio")
        if not self.origin.strip():
            raise ValueError("TrustEnvelope: origin vazio")
        if self.trust not in {TrustLabel.SYSTEM, TrustLabel.POLICY}:
            if self.instruction_authority in {
                InstructionAuthority.SYSTEM,
                InstructionAuthority.POLICY,
            }:
                raise ValueError("external/data trust cannot carry system or policy authority")

    @property
    def id(self) -> str:
        return f"trust_{_digest(self.to_dict(include_id=False))}"

    def to_dict(self, *, include_id: bool = True) -> dict[str, Any]:
        result = asdict(self)
        result["trust"] = self.trust.value
        result["instruction_authority"] = self.instruction_authority.value
        result["taint"] = self.taint.value
        result["provenance"] = list(self.provenance)
        if include_id:
            result = {"id": self.id, **result}
        return result

    @classmethod
    def external(
        cls, content: str, *, origin: str, provenance: Iterable[str] = ()
    ) -> TrustEnvelope:
        lowered = content.lower()
        suspicious = any(marker in lowered for marker in _INJECTION_MARKERS)
        return cls(
            content=content,
            origin=origin,
            trust=TrustLabel.EXTERNAL_UNTRUSTED if suspicious else TrustLabel.EXTERNAL_DATA,
            instruction_authority=InstructionAuthority.DATA_ONLY,
            taint=Taint.SUSPICIOUS if suspicious else Taint.EXTERNAL,
            provenance=tuple(provenance),
        )

    def as_verified_fact(self, *, fact_ref: str, freshness: str = "verified") -> TrustEnvelope:
        """Upgrade factual trust only; instruction authority remains data-only."""
        return TrustEnvelope(
            content=self.content,
            origin=self.origin,
            trust=TrustLabel.VERIFIED_FACT,
            scope=self.scope,
            instruction_authority=InstructionAuthority.DATA_ONLY,
            taint=self.taint,
            provenance=(*self.provenance, fact_ref),
            freshness=freshness,
            content_kind="fact",
        )


@dataclass(frozen=True, slots=True)
class RoleContextPlan:
    """Least-context plan for one role; no role receives unrestricted context."""

    role: str
    allowed_context: tuple[str, ...] = ()
    required_context: tuple[str, ...] = ()
    context_share: float = 1.0
    artifact_access: tuple[str, ...] = ()
    memory_access: tuple[str, ...] = ()
    knowledge_access: tuple[str, ...] = ()
    tool_access: tuple[str, ...] = ()
    trust_floor: TrustLabel = TrustLabel.UNKNOWN

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ValueError("RoleContextPlan: role vazio")
        if not 0 < self.context_share <= 1:
            raise ValueError("RoleContextPlan: context_share deve estar em (0, 1]")

    def allows(self, kind: str, *, trust: TrustLabel = TrustLabel.UNKNOWN) -> bool:
        allowed = not self.allowed_context or kind in self.allowed_context
        return allowed and TRUST_RANK[trust] >= TRUST_RANK[self.trust_floor]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in (
            "allowed_context",
            "required_context",
            "artifact_access",
            "memory_access",
            "knowledge_access",
            "tool_access",
        ):
            result[key] = list(result[key])
        result["trust_floor"] = self.trust_floor.value
        return result

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> RoleContextPlan:
        """Reconstroi o plano serializado (fronteira MCP/CLI viaja como dict).

        Valores invalidos levantam `ValueError`/`KeyError` -- quem chama
        (`ContextGateway`) converte em `role_plan_invalid` nomeado, porque um
        plano malformado NAO pode ser lido como "sem plano" (fail-open).
        """
        if not isinstance(raw, Mapping):
            raise ValueError("role_plan must be a mapping")
        return cls(
            role=str(raw.get("role", "")),
            allowed_context=tuple(str(k) for k in raw.get("allowed_context", ())),
            required_context=tuple(str(k) for k in raw.get("required_context", ())),
            context_share=float(raw.get("context_share", 1.0)),
            artifact_access=tuple(str(k) for k in raw.get("artifact_access", ())),
            memory_access=tuple(str(k) for k in raw.get("memory_access", ())),
            knowledge_access=tuple(str(k) for k in raw.get("knowledge_access", ())),
            tool_access=tuple(str(k) for k in raw.get("tool_access", ())),
            trust_floor=TrustLabel(str(raw.get("trust_floor", "UNKNOWN"))),
        )


@dataclass(frozen=True, slots=True)
class AgentHandoff:
    """Data-only cross-agent handoff with an explicit requested action.

    `trust` e `taint` sao declaracoes do remetente, nao medidas: quem admite
    (`admit_handoff`) aplica teto e varredura antes de acreditar nelas.
    `context_items` carrega itens de contexto arbitrarios com `kind` proprio
    (o ponto por onde `tool_output` cru poderia tentar entrar). `origin` no
    formato `agent:<role>` permite conferir remetente declarado contra
    origem declarada — divergencia e impersonacao, nao rotulo livre.
    """

    sender_role: str
    recipient_role: str
    facts: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    requested_action: str = ""
    authority: InstructionAuthority = InstructionAuthority.DATA_ONLY
    origin: str = ""
    scope: str = ""
    trust: TrustLabel = TrustLabel.UNKNOWN
    taint: Taint = Taint.EXTERNAL
    context_items: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not self.sender_role.strip() or not self.recipient_role.strip():
            raise ValueError("AgentHandoff: sender_role e recipient_role obrigatórios")
        if self.authority != InstructionAuthority.DATA_ONLY:
            raise ValueError("AgentHandoff: mensagens entre agentes são DATA_ONLY")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in (
            "facts",
            "assumptions",
            "hypotheses",
            "recommendations",
            "unresolved",
            "evidence_refs",
            "context_items",
        ):
            result[key] = list(result[key])
        result["authority"] = self.authority.name
        result["trust"] = self.trust.value
        result["taint"] = self.taint.value
        return result

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> AgentHandoff:
        """Reconstroi o handoff serializado na fronteira entre agentes.

        Invalido levanta -- quem admite (`admit_handoff`) converte em DENY
        nomeado, porque um handoff malformado NAO pode ser lido como benigno.
        """
        if not isinstance(raw, Mapping):
            raise ValueError("AgentHandoff: entrada deve ser um mapping")
        return cls(
            sender_role=str(raw.get("sender_role", "")),
            recipient_role=str(raw.get("recipient_role", "")),
            facts=tuple(str(x) for x in raw.get("facts", ())),
            assumptions=tuple(str(x) for x in raw.get("assumptions", ())),
            hypotheses=tuple(str(x) for x in raw.get("hypotheses", ())),
            recommendations=tuple(str(x) for x in raw.get("recommendations", ())),
            unresolved=tuple(str(x) for x in raw.get("unresolved", ())),
            evidence_refs=tuple(str(x) for x in raw.get("evidence_refs", ())),
            requested_action=str(raw.get("requested_action", "")),
            authority=InstructionAuthority(str(raw.get("authority", "data_only")).lower()),
            origin=str(raw.get("origin", "")),
            scope=str(raw.get("scope", "")),
            trust=TrustLabel(str(raw.get("trust", "UNKNOWN"))),
            taint=Taint(str(raw.get("taint", "external"))),
            context_items=tuple(
                dict(item)
                for item in raw.get("context_items", ())
                if isinstance(item, Mapping)
            ),
        )


def sanitize_tool_output(content: str, *, origin: str) -> TrustEnvelope:
    """Wrap tool output as data and flag suspicious instruction-shaped text."""
    return TrustEnvelope.external(content, origin=origin)


def tool_result_envelope(content: str, *, origin: str) -> TrustEnvelope:
    """Tool output is `TOOL_OUTPUT` even when its text looks like an instruction.

    `TrustEnvelope.external` rotula proveniencia generica (`EXTERNAL_DATA`);
    resultado de tool tem proveniencia propria. A suspeicao mora em `taint`,
    nao no label -- dizer "isto veio de uma tool" continua verdade quando o
    conteudo e hostil.
    """
    return replace(
        TrustEnvelope.external(content, origin=origin), trust=TrustLabel.TOOL_OUTPUT
    )


__all__ = [
    "AgentHandoff",
    "InstructionAuthority",
    "RoleContextPlan",
    "Taint",
    "TRUST_RANK",
    "TrustEnvelope",
    "TrustLabel",
    "sanitize_tool_output",
    "tool_result_envelope",
]
