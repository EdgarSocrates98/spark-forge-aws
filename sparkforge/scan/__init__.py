"""`sparkforge scan` (§22): roda sozinho os analyzes que cabem num repositorio."""
from sparkforge.scan.plan import (
    KIND_PARA_ANALYZE,
    RECUSAS,
    Entrada,
    Plano,
    Recusa,
    ScanError,
    plan,
)
from sparkforge.scan.summary import gate, resumo

__all__ = [
    "KIND_PARA_ANALYZE",
    "RECUSAS",
    "Entrada",
    "Plano",
    "Recusa",
    "ScanError",
    "gate",
    "plan",
    "resumo",
]
