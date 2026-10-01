"""Autonomia L1-L2 do §15: produzir a mudanca (`plan`) e executa-la numa copia (`sandbox`).

Os dois estagios usam o nome do §15 (`produce_change`, `sandbox_execute`) num
campo `stage` proprio, e NAO o enum `AutonomyLevel` de `agentic/autonomy.py`:
la L1/L2 sao Specialist/Cooperative, outra escala. Nada aqui chama provider,
subprocess ou git, e nada escreve na arvore do operador fora de
`.sparkforge/sandbox/`.
"""
from __future__ import annotations

from sparkforge.change.apply import DIFF_MAX_BYTES, Patch, apply_patches, parse_unified_diff
from sparkforge.change.plan import STAGE_PLAN, plan_change
from sparkforge.change.proposal import STAGE_PROPOSAL, ProposalDefect, montar
from sparkforge.change.refusals import (
    DESTRAVA,
    RECUSAS_DA_PROPOSTA,
    RECUSAS_DO_PLANO,
    RECUSAS_DO_SANDBOX,
    ChangeError,
)
from sparkforge.change.sandbox import STAGE_SANDBOX, executar, limpar, recusa

__all__ = [
    "DESTRAVA",
    "DIFF_MAX_BYTES",
    "RECUSAS_DA_PROPOSTA",
    "RECUSAS_DO_PLANO",
    "RECUSAS_DO_SANDBOX",
    "STAGE_PLAN",
    "STAGE_PROPOSAL",
    "STAGE_SANDBOX",
    "ChangeError",
    "Patch",
    "ProposalDefect",
    "apply_patches",
    "executar",
    "limpar",
    "montar",
    "parse_unified_diff",
    "plan_change",
    "recusa",
]
