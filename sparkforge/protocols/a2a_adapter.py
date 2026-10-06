"""Adapter A2A experimental sobre o Forge Protocol (§110-114).

Arquitetura — o Forge Protocol e o contrato; este modulo so traduz
formas, nos dois sentidos:

    A2A → adapter → Forge Protocol → Spark Forge

`A2A-ready` e o rótulo honesto (§110): isto NAO e uma implementacao do
protocolo A2A — e a camada de traducao que um SDK A2A real usaria. Nenhum
pacote `a2a` entra como dependencia (§112): tudo aqui e stdlib-puro e os
tipos sao os de `sparkforge.protocols.forge`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sparkforge.protocols.forge import (
    ForgeCapability,
    ForgeResult,
    ForgeTask,
    ForgeTaskStatus,
)

A2A_EXPERIMENTAL: dict[str, Any] = {
    "experimental": True,
    # Forge Protocol — A2A-ready (§110). Nunca "implementacao A2A".
    "compatibility": "a2a-ready",
    "spec_reviewed": False,  # §113: avaliacao da spec vigente pendente
}

# Estados de task do vocabulario A2A vigente. O mapeamento e declarado
# aqui de proposito: trocar a spec exige diff visivel, nao heuristica.
_STATE_MAP: dict[ForgeTaskStatus, str] = {
    ForgeTaskStatus.ACCEPTED: "submitted",
    ForgeTaskStatus.RUNNING: "working",
    ForgeTaskStatus.SUCCEEDED: "completed",
    ForgeTaskStatus.FAILED: "failed",
    ForgeTaskStatus.BLOCKED: "rejected",
    # `unknown` e o estado A2A para "o servidor nao sabe" — a forma honesta
    # de carregar `unresolved` sem fingir sucesso nem falha.
    ForgeTaskStatus.UNRESOLVED: "unknown",
}


def forge_to_a2a_state(status: ForgeTaskStatus) -> str:
    return _STATE_MAP[status]


def agent_card(
    capabilities: Sequence[ForgeCapability],
    *,
    name: str,
    version: str,
    url: str,
) -> dict[str, Any]:
    """AgentCard na forma A2A, preenchida por ForgeCapability (§113-114).

    O conteudo flui Forge→A2A, nunca o contrario: quem descobre o card ve
    exatamente as capacidades que o Forge ja declara.
    """
    caps = list(capabilities)
    for cap in caps:
        if not isinstance(cap, ForgeCapability):
            raise TypeError("agent_card so publica ForgeCapability")
    return {
        "name": name,
        "version": version,
        "url": url,
        "protocol": {"forge": "1", "a2a": A2A_EXPERIMENTAL["compatibility"]},
        "defaultInputModes": ["application/forge-task+json"],
        "defaultOutputModes": ["application/forge-result+json"],
        "capabilities": [cap.to_dict() for cap in caps],
        "skills": [
            {
                "id": cap.name,
                "name": cap.name,
                "description": f"Forge capability {cap.name} v{cap.version}",
                "tags": list(cap.domains),
            }
            for cap in caps
        ],
        "experimental": True,
    }


def submit_task(params: Mapping[str, Any]) -> ForgeTask:
    """`tasks/send` A2A (message+parts) → `ForgeTask` (§113, §114).

    O `objective` sai da parte `text`; partes `data` viram `inputs`.
    `metadata.requested_by`/`risk` passam direto — a autoridade do Forge
    decide o que fazer com eles depois.
    """
    if not isinstance(params, Mapping):
        raise ValueError("params de submit_task deve ser um mapping")
    message = params.get("message") or {}
    parts = message.get("parts") or ()
    texts: list[str] = []
    inputs: dict[str, Any] = {}
    for part in parts:
        if not isinstance(part, Mapping):
            continue
        if part.get("kind") == "text" and part.get("text"):
            texts.append(str(part["text"]))
        elif part.get("kind") == "data" and isinstance(part.get("data"), Mapping):
            inputs.update(part["data"])
    objective = " ".join(texts).strip()
    if not objective:
        raise ValueError("submit_task exige objective: ao menos uma parte text")
    metadata = params.get("metadata") or {}
    return ForgeTask(
        task_type=str(metadata.get("task_type") or "forge_task"),
        objective=objective,
        inputs=inputs,
        budget=dict(metadata.get("budget") or {}),
        requested_by=str(metadata.get("requested_by") or ""),
        risk=str(metadata.get("risk") or "read_only"),
    )


def result_to_a2a_task(result: ForgeResult) -> dict[str, Any]:
    """`ForgeResult` → task A2A com artifacts (§113-114).

    `evidence` vira o artifact `evidence_bundle`; `unresolved` vira o
    artifact `unresolved` — nunca absorvido pelo `summary` nem marcado
    como `completed`.
    """
    artifacts: list[dict[str, Any]] = [
        {
            "name": "evidence_bundle",
            "parts": [{"kind": "data", "data": result.evidence.to_dict()}],
        }
    ]
    if result.evidence.unresolved:
        artifacts.append(
            {
                "name": "unresolved",
                "parts": [
                    {"kind": "data", "data": {"unresolved": list(result.evidence.unresolved)}}
                ],
            }
        )
    return {
        "id": result.task_id,
        "status": {"state": forge_to_a2a_state(result.status)},
        "artifacts": artifacts,
        "metadata": {"summary": result.summary, "metrics": dict(result.metrics)},
        "experimental": True,
    }


__all__ = [
    "A2A_EXPERIMENTAL",
    "agent_card",
    "forge_to_a2a_state",
    "result_to_a2a_task",
    "submit_task",
]
