"""Admission de AgentHandoff — o plano de contexto do receptor governa.

    AgentHandoff -> RoleContextPlan do receptor -> ALLOW / DENY / REVIEW

O que atravessa a fronteira entre agentes e data, nunca instrucao:

- DATA_ONLY nao muda atravessando a fronteira; um handoff serializado que
  declare outra autoridade nao chega a existir como objeto (o construtor
  recusa) e a admissao converte a tentativa em DENY nomeado;
- `trust` declarado e teto-limitado a MODEL_OUTPUT — auto-declaracao nao
  verifica (mesmo molde de `classify_memory_candidate`, que nao acredita no
  `trust` do proprio registro). O trust de um Fact mora no registro do case,
  nao no rotulo que o remetente afirma;
- `taint` declarado POISONED nega; texto com marcador lexical de instrucao
  (`detect_prompt_injection`, o mesmo guardrail do `_trust` de `call_tool`)
  sobe o taint efetivo para SUSPICIOUS e a decisao vira REVIEW — o conteudo
  segue como dado marcado, nao e apagado nem executado;
- cada seccao entra como o kind que ela E (fact, assumption, hypothesis,
  recommendation, unresolved, evidence) e cada `context_items` entra com o
  `kind` declarado — `plan.allows(kind, trust)` decide item a item, e a
  negacao vira `unresolved` nomeado, nunca sumico;
- `requested_action` que nomeia uma tool da superficie declarada e
  verificado contra o `tool_access` do remetente: pedir o que o proprio
  remetente nao pode invocar e confused deputy — DENY. Sem plano do
  remetente a autoridade do pedido nao e verificavel — REVIEW. O mesmo
  pedido contra o `tool_access` do receptor negado vira REVIEW nomeado;
- `required_context` NAO e avaliado aqui: o requisito do papel se cumpre no
  contexto total (rules vem do catalogo, nao do handoff). A selecao final no
  ContextGateway continua emitindo `required_context_missing`.

Decisao REVIEW nao finge ALLOW: `admitted` existe, e `reasons`/`unresolved`
dizem o que precisa ser visto antes de consumir. DENY nao devolve conteudo.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from sparkforge.agentic.role_plans import role_plan
from sparkforge.agentic.security import detect_prompt_injection
from sparkforge.agentic.trust import (
    TRUST_RANK,
    AgentHandoff,
    RoleContextPlan,
    Taint,
    TrustLabel,
)


class HandoffDecision(str, Enum):
    """Vocabulario do gate: o que o plano do receptor decidiu."""

    ALLOW = "allow"
    DENY = "deny"
    REVIEW = "review"


# Teto de trust para conteudo escrito por agente: a embalagem e MODEL_OUTPUT.
# Um Fact verificado dentro do handoff continua verificado no registro do
# case — a etiqueta do envelope nao precisa e nao pode atestar isso.
TRUST_CEILING = TrustLabel.MODEL_OUTPUT

# Cada seccao fixa do handoff entra no contexto como o kind que ela E.
# `assumption`/`hypothesis`/`recommendation` nao constam de nenhum plano dos
# cinco executores de proposito: ninguem le a suposicao do outro de graca.
_SECTION_KIND: dict[str, str] = {
    "facts": "fact",
    "assumptions": "assumption",
    "hypotheses": "hypothesis",
    "recommendations": "recommendation",
    "unresolved": "unresolved",
    "evidence_refs": "evidence",
}


def _unresolved(code: str, message: str, unlock: str | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"code": code, "message": message}
    if unlock is not None:
        entry["unlock"] = unlock
    return entry


def _effective_trust(declared: TrustLabel) -> TrustLabel:
    """Teto MODEL_OUTPUT sobre a etiqueta declarada — auto-declaracao nao
    verifica. Etiqueta abaixo do teto passa intocada."""
    if TRUST_RANK[declared] > TRUST_RANK[TRUST_CEILING]:
        return TRUST_CEILING
    return declared


def _item_trust(item: Mapping[str, Any], fallback: TrustLabel) -> TrustLabel:
    """Etiqueta do item, caindo na do envelope quando ausente; invalida ou
    acima do teto resolve para a medida honesta (UNKNOWN / MODEL_OUTPUT)."""
    raw = item.get("trust")
    if raw is None:
        return fallback
    try:
        return _effective_trust(TrustLabel(str(raw)))
    except ValueError:
        return TrustLabel.UNKNOWN


def _item_kind(item: Mapping[str, Any]) -> str:
    raw = item.get("kind", item.get("type", "context"))
    return str(raw).split(".", 1)[0].lower()


_TAINT_RANK = {
    Taint.CLEAN: 0,
    Taint.EXTERNAL: 1,
    Taint.SUSPICIOUS: 2,
    Taint.POISONED: 3,
}


def _item_taint(item: Mapping[str, Any], floor: Taint) -> Taint:
    """Taint efetivo do item: o declarado proprio nunca e rebaixado pelo do
    envelope — sobe quando o envelope esta pior ou quando ele mesmo declara."""
    raw = item.get("taint")
    try:
        declared = Taint(str(raw)) if raw is not None else floor
    except ValueError:
        declared = floor
    return declared if _TAINT_RANK[declared] >= _TAINT_RANK[floor] else floor


def _scan_taint(handoff: AgentHandoff) -> Taint:
    """Taint efetivo: o declarado e o piso; a varredura lexical so pode
    subir. Conteudo de agente e dado — texto com cara de instrucao marca
    SUSPICIOUS, nunca e apagado."""
    declared = handoff.taint
    if declared == Taint.POISONED:
        return Taint.POISONED
    textos: list[str] = []
    for field in _SECTION_KIND:
        textos.extend(str(v) for v in getattr(handoff, field))
    textos.append(handoff.requested_action)
    for item in handoff.context_items:
        textos.extend(str(v) for v in item.values() if isinstance(v, str))
    suspeito = any(
        not detect_prompt_injection(texto).passed for texto in textos if texto
    )
    if suspeito or declared == Taint.SUSPICIOUS:
        return Taint.SUSPICIOUS
    return declared


def _resolve_plan(
    handoff: AgentHandoff,
    *,
    receiver: str | None,
    plan: RoleContextPlan | Mapping[str, Any] | None,
) -> RoleContextPlan | dict[str, Any]:
    """O plano do receptor, ou o dict de DENY que a falha produz.

    `plan` explicito vence `receiver` nominal, que vence `recipient_role` do
    proprio handoff — a fronteira e o remetente quem diz para quem vai, e a
    admissao confere. Plano malformado ou role sem registro NAO abrem a
    fronteira: viram DENY nomeado, mesmo molde do `_DenyAll` do gateway.
    """
    if plan is not None:
        try:
            return (
                plan if isinstance(plan, RoleContextPlan) else RoleContextPlan.from_dict(plan)
            )
        except (TypeError, ValueError, KeyError) as exc:
            return {
                "reason": "handoff_receiver_plan_invalid",
                "detail": f"receiver plan malformado: {exc}",
            }
    nome = receiver or handoff.recipient_role
    resolved = role_plan(nome)
    if resolved is None:
        return {
            "reason": "handoff_receiver_plan_unknown",
            "detail": f"role {nome!r} sem plano declarado em ROLE_PLANS",
        }
    return resolved


@dataclass(frozen=True, slots=True)
class HandoffAdmission:
    """Recibo da admissao: decisao, o que entrou e o que ficou nomeado."""

    decision: HandoffDecision
    sender_role: str
    recipient_role: str
    authority: str  # sempre "DATA_ONLY" — a fronteira nunca sobe autoridade
    trust: TrustLabel
    taint: Taint
    admitted: AgentHandoff | None
    denied: tuple[str, ...]
    reasons: tuple[str, ...]
    unresolved: tuple[dict[str, Any], ...]

    @property
    def id(self) -> str:
        return f"hadm_{_digest_of(self.to_dict(include_id=False))}"

    def context_items(self) -> tuple[dict[str, Any], ...]:
        """O conteudo admitido no formato de item do ContextGateway.

        Composicao sem sub-sistema novo: a admissao filtra, o gateway mede
        orcamento e relevancia — e, como aplica o MESMO plano do receptor,
        re-filtra de graca (defesa em profundidade que nunca contradiz).
        """
        if self.admitted is None:
            return ()
        h = self.admitted
        origem = h.origin or f"agent:{h.sender_role}"
        provenance = f"handoff:{h.sender_role}->{h.recipient_role}"
        items: list[dict[str, Any]] = []
        for field, kind in _SECTION_KIND.items():
            for i, value in enumerate(getattr(h, field)):
                items.append(
                    {
                        "id": f"handoff:{field}:{i}",
                        "kind": kind,
                        "trust": h.trust.value,
                        "taint": h.taint.value,
                        "origin": origem,
                        "provenance": provenance,
                        "content": value,
                    }
                )
        for item in h.context_items:
            merged = dict(item)
            merged.setdefault("id", f"handoff:item:{len(items)}")
            merged["origin"] = origem
            merged["provenance"] = provenance
            # a admissao ja normalizou o taint por item — nao rebaixar aqui
            merged["taint"] = str(item.get("taint") or h.taint.value)
            items.append(merged)
        return tuple(items)

    def to_dict(self, *, include_id: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "decision": self.decision.value,
            "sender_role": self.sender_role,
            "recipient_role": self.recipient_role,
            "authority": self.authority,
            "trust": self.trust.value,
            "taint": self.taint.value,
            "admitted": self.admitted.to_dict() if self.admitted is not None else None,
            "denied": list(self.denied),
            "reasons": list(self.reasons),
            "unresolved": [dict(u) for u in self.unresolved],
        }
        if include_id:
            result = {"id": self.id, **result}
        return result


def _digest_of(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _deny(
    reason: str,
    detail: str,
    *,
    sender_role: str = "",
    recipient_role: str = "",
    trust: TrustLabel = TrustLabel.UNKNOWN,
    taint: Taint = Taint.EXTERNAL,
    denied: tuple[str, ...] = (),
    unresolved: tuple[dict[str, Any], ...] = (),
    reasons: tuple[str, ...] = (),
) -> HandoffAdmission:
    entry = _unresolved(reason, detail)
    return HandoffAdmission(
        decision=HandoffDecision.DENY,
        sender_role=sender_role,
        recipient_role=recipient_role,
        authority="DATA_ONLY",
        trust=trust,
        taint=taint,
        admitted=None,
        denied=denied,
        reasons=(reason, *reasons),
        unresolved=(entry, *unresolved),
    )


def admit_handoff(
    handoff: AgentHandoff | Mapping[str, Any],
    *,
    receiver: str | None = None,
    plan: RoleContextPlan | Mapping[str, Any] | None = None,
    sender_plan: RoleContextPlan | Mapping[str, Any] | None = None,
    tool_names: Collection[str] | None = None,
) -> HandoffAdmission:
    """Admite um AgentHandoff contra o plano de contexto do receptor.

    `receiver`/`plan` resolvem a politica (plano explicito vence nome de
    role, que vence `recipient_role` do handoff). `sender_plan` e a prova de
    autoridade do remetente para a checagem de confused deputy — sem ele, um
    pedido que nomeia tool sai REVIEW, nunca ALLOW silencioso. `tool_names`
    e a superficie de tools conhecida do chamador (ex.: `TOOLS` do adapter);
    sem ela, `requested_action` livre nao e presumido pedido de tool.
    """
    if isinstance(handoff, AgentHandoff):
        h = handoff
    elif isinstance(handoff, Mapping):
        try:
            h = AgentHandoff.from_dict(handoff)
        except (TypeError, ValueError, KeyError) as exc:
            reason = (
                "handoff_authority_not_data_only"
                if "DATA_ONLY" in str(exc)
                else "handoff_malformed"
            )
            return _deny(
                reason,
                str(exc),
                sender_role=str(handoff.get("sender_role", "")),
                recipient_role=str(handoff.get("recipient_role", "")),
            )
    else:
        return _deny(
            "handoff_malformed",
            f"handoff deve ser AgentHandoff ou mapping, recebeu {type(handoff).__name__}",
        )

    resolved = _resolve_plan(h, receiver=receiver, plan=plan)
    if isinstance(resolved, dict):
        return _deny(
            str(resolved["reason"]),
            str(resolved["detail"]),
            sender_role=h.sender_role,
            recipient_role=h.recipient_role,
        )
    receiver_plan = resolved
    if receiver_plan.role != h.recipient_role:
        return _deny(
            "handoff_recipient_mismatch",
            f"handoff para {h.recipient_role!r} admitido contra plano de "
            f"{receiver_plan.role!r}",
            sender_role=h.sender_role,
            recipient_role=h.recipient_role,
        )
    if h.origin.startswith("agent:") and h.origin != f"agent:{h.sender_role}":
        return _deny(
            "handoff_sender_origin_mismatch",
            f"origin {h.origin!r} declara outro agente que sender_role "
            f"{h.sender_role!r}",
            sender_role=h.sender_role,
            recipient_role=h.recipient_role,
        )

    effective_trust = _effective_trust(h.trust)
    effective_taint = _scan_taint(h)
    if effective_taint == Taint.POISONED:
        return _deny(
            "handoff_taint_poisoned",
            "taint poisoned declarado ou detectado — nada atravessa",
            sender_role=h.sender_role,
            recipient_role=h.recipient_role,
            trust=effective_trust,
            taint=effective_taint,
        )

    unresolved: list[dict[str, Any]] = []
    reasons: list[str] = []
    denied: list[str] = []

    # Confused deputy: o pedido so e verificavel quando nomeia uma tool da
    # superficie que o chamador declarou. Pedido de tool fora do tool_access
    # restrito do remetente e escalacao de privilegio — DENY. Sem plano do
    # remetente, a autoridade do pedido e unverified — REVIEW.
    action = h.requested_action.strip()
    if action and tool_names is not None and action in tool_names:
        sender = _resolve_sender_plan(sender_plan)
        if sender is None:
            unresolved.append(
                _unresolved(
                    "handoff_sender_authority_unverified",
                    f"pedido de tool {action!r} sem plano valido do remetente "
                    f"{h.sender_role!r} para conferir tool_access",
                    "passe sender_plan declarando o tool_access do remetente",
                )
            )
            reasons.append("handoff_sender_authority_unverified")
        elif sender.tool_access and action not in sender.tool_access:
            return _deny(
                "handoff_confused_deputy",
                f"remetente {h.sender_role!r} pede tool {action!r} fora do "
                f"proprio tool_access {list(sender.tool_access)}",
                sender_role=h.sender_role,
                recipient_role=h.recipient_role,
                trust=effective_trust,
                taint=effective_taint,
                unresolved=tuple(unresolved),
            )
        if receiver_plan.tool_access and action not in receiver_plan.tool_access:
            unresolved.append(
                _unresolved(
                    "handoff_tool_denied_for_receiver",
                    f"tool {action!r} fora do tool_access do receptor "
                    f"{receiver_plan.role!r}",
                    "o pedido chega como dado; a tool nao e executavel pelo receptor",
                )
            )
            reasons.append("handoff_tool_denied_for_receiver")

    # Seccao a seccao pelo kind que ela E; item a item pelo kind declarado.
    # `allows` falha fecha: fora de allowed_context ou abaixo do floor vira
    # unresolved nomeado, e o que fica nunca e reescrito.
    admitted: dict[str, Any] = {}
    for field, kind in _SECTION_KIND.items():
        values = getattr(h, field)
        if not values:
            continue
        if receiver_plan.allows(kind, trust=effective_trust):
            admitted[field] = values
        else:
            denied.append(field)
            unresolved.append(
                _unresolved(
                    "handoff_section_denied",
                    f"seccao {field} (kind={kind}, trust={effective_trust.value}) "
                    f"fora do plano de {receiver_plan.role}",
                    "declare o kind em allowed_context ou suba o trust da fonte",
                )
            )

    admitted_items: list[dict[str, Any]] = []
    for i, item in enumerate(h.context_items):
        kind = _item_kind(item)
        itrust = _item_trust(item, effective_trust)
        if receiver_plan.allows(kind, trust=itrust):
            admitted_items.append(
                {
                    **dict(item),
                    "trust": itrust.value,
                    "taint": _item_taint(item, effective_taint).value,
                    "origin": h.origin or f"agent:{h.sender_role}",
                    "provenance": f"handoff:{h.sender_role}->{h.recipient_role}",
                }
            )
        else:
            item_id = str(item.get("id") or f"context_items[{i}]")
            denied.append(item_id)
            unresolved.append(
                _unresolved(
                    "handoff_item_denied",
                    f"item {item_id} (kind={kind}, trust={itrust.value}) "
                    f"fora do plano de {receiver_plan.role}",
                    "declare o kind em allowed_context ou suba o trust da fonte",
                )
            )

    if not admitted and not admitted_items:
        return _deny(
            "handoff_nothing_admissible",
            "nenhuma seccao ou item do handoff e admissivel pelo plano do "
            "receptor — nada atravessa",
            sender_role=h.sender_role,
            recipient_role=h.recipient_role,
            trust=effective_trust,
            taint=effective_taint,
            denied=tuple(denied),
            unresolved=tuple(unresolved),
        )

    if effective_taint == Taint.SUSPICIOUS:
        reasons.append("handoff_taint_suspicious")

    cleared_sections: dict[str, Any] = {
        field: () for field in denied if field in _SECTION_KIND
    }
    filtered = replace(
        h,
        context_items=tuple(admitted_items),
        trust=effective_trust,
        taint=effective_taint,
        **cleared_sections,
    )
    decision = HandoffDecision.REVIEW if reasons else HandoffDecision.ALLOW
    return HandoffAdmission(
        decision=decision,
        sender_role=h.sender_role,
        recipient_role=h.recipient_role,
        authority="DATA_ONLY",
        trust=effective_trust,
        taint=effective_taint,
        admitted=filtered,
        denied=tuple(denied),
        reasons=tuple(reasons),
        unresolved=tuple(unresolved),
    )


def _resolve_sender_plan(
    sender_plan: RoleContextPlan | Mapping[str, Any] | None,
) -> RoleContextPlan | None:
    """O plano do remetente quando declarado e valido; invalido conta como
    ausente — a chamada nao pode fingir a autoridade que nao conseguiu ler."""
    if sender_plan is None:
        return None
    if isinstance(sender_plan, RoleContextPlan):
        return sender_plan
    try:
        return RoleContextPlan.from_dict(sender_plan)
    except (TypeError, ValueError, KeyError):
        return None


__all__ = [
    "HandoffAdmission",
    "HandoffDecision",
    "TRUST_CEILING",
    "admit_handoff",
]
