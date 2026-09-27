"""Public, provider-independent entry point for incremental Code Intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.codeintel.staleness import ResultadoSync, sincronizar


@dataclass(frozen=True, slots=True)
class IncrementalRefresh:
    """Serializable report for a refresh of one worktree index."""

    schema_version: int
    root: str
    database: str
    complete: bool
    scanned_files: int
    reused_files: int
    changed_files: tuple[str, ...]
    affected_files: tuple[str, ...]
    updated_symbols: int
    unresolved_references: int
    duration_s: float
    tree_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root": self.root,
            "database": self.database,
            "complete": self.complete,
            "scanned_files": self.scanned_files,
            "reused_files": self.reused_files,
            "changed_files": list(self.changed_files),
            "affected_files": list(self.affected_files),
            "updated_symbols": self.updated_symbols,
            "unresolved_references": self.unresolved_references,
            "duration_s": self.duration_s,
            "tree_fingerprint": self.tree_fingerprint,
        }


def refresh(
    root: str | Path,
    database: str | Path | None = None,
) -> IncrementalRefresh:
    """Refresh ``database`` and expose changed/affected worktree evidence.

    The implementation delegates to the existing fail-closed staleness engine;
    this module is deliberately an API boundary, not a second indexer.
    """

    base = Path(root).expanduser().resolve()
    target = Path(database).expanduser() if database is not None else None
    if target is None:
        from sparkforge.codeintel.staleness import banco_da_arvore

        target = banco_da_arvore(base)
    target = target.resolve()
    result: ResultadoSync = sincronizar(base, target)
    changed = (
        *result.mudancas.alterados,
        *result.mudancas.novos,
        *result.mudancas.removidos,
    )
    affected = tuple(sorted(set(changed) | set(result.reresolvidos)))
    scanned = result.arquivos + len(result.mudancas.removidos)
    reused = max(0, scanned - len(changed))
    return IncrementalRefresh(
        schema_version=1,
        root=base.as_posix(),
        database=target.as_posix(),
        complete=result.completa,
        scanned_files=scanned,
        reused_files=reused,
        changed_files=tuple(sorted(changed)),
        affected_files=affected,
        updated_symbols=result.nos,
        unresolved_references=result.nao_resolvidas,
        duration_s=result.duracao_s,
        tree_fingerprint=result.estado.fingerprint,
    )


__all__ = ["IncrementalRefresh", "refresh"]
