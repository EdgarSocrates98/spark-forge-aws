"""Em que fase cada feature esta, e o que a impede de avancar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.paths import resolve_within
from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.checks import check
from sparkforge.sdd.load import discover, load_artifact


def status(repo: Path | str, root: str = DEFAULT_ROOT) -> dict[str, Any]:
    relatorio = check(repo, root)
    raiz = resolve_within(Path(repo), root)
    if raiz is None or not raiz.is_dir():
        return {"root": root, "features": [], "unresolved": relatorio["unresolved"]}
    itens: list[dict[str, Any]] = []
    for nome, caminhos in sorted(discover(raiz).items()):
        atual = max(caminhos, key=PHASES.index)
        meta = load_artifact(caminhos[atual]).meta or {}
        posicao = PHASES.index(atual)
        itens.append({
            "feature": nome,
            "phase": atual,
            "status": meta.get("status"),
            "profile": meta.get("profile"),
            "next_phase": PHASES[posicao + 1] if posicao + 1 < len(PHASES) else None,
            "refused": sorted({r["code"] for r in relatorio["refused"] if r["feature"] == nome}),
            "unresolved": sorted(
                {u["code"] for u in relatorio["unresolved"] if u["feature"] == nome}
            ),
        })
    return {"root": root, "features": itens, "unresolved": []}
