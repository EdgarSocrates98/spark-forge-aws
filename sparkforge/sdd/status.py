"""Em que fase cada feature esta, e o que a impede de avancar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.checks import evaluate


def status(repo: Path | str, root: str = DEFAULT_ROOT) -> dict[str, Any]:
    # a mesma passada do `check`: fase, status e recusas saem dos mesmos arquivos
    relatorio, contextos = evaluate(repo, root, None)
    itens: list[dict[str, Any]] = []
    for nome, ctx in sorted(contextos.items()):
        atual = max(ctx.caminhos, key=PHASES.index)
        # artefato recusado pelo schema nao tem status nem profile confiaveis
        artefato = ctx.artefatos.get(atual)
        meta = artefato.meta if artefato is not None else {}
        posicao = PHASES.index(atual)
        itens.append({
            "feature": nome,
            "phase": atual,
            "status": meta.get("status"),
            "profile": meta.get("profile"),
            "next_phase": PHASES[posicao + 1] if posicao + 1 < len(PHASES) else None,
            "refused": sorted({r["code"] for r in ctx.refused}),
            "unresolved": sorted(
                {u["code"] for u in relatorio["unresolved"] if u["feature"] == nome}
            ),
        })
    # lacuna sem feature descoberta (pasta podada, arquivo na raiz, raiz ausente)
    # nao tem linha propria na lista; sobe para o topo para nao sumir
    orfas = [u for u in relatorio["unresolved"] if u["feature"] not in contextos]
    return {"root": root, "features": itens, "unresolved": orfas}
