"""Ferramental de apoio ao agente: contexto, custo, avaliacao, lineage e offline.

Reexporta a superficie publica para que quem consome escreva
`from sparkforge.tools import estimate_tokens` sem depender do modulo interno
onde a funcao mora hoje.
"""
from .context import pack_context
from .cost import budget_report, estimate_tokens
from .evaluation import evaluate_golden_case
from .lineage import extract_lineage_edges
from .offline import OfflineKnowledgeIndex
from .schema import compare_json_schemas

__all__ = [
    "OfflineKnowledgeIndex",
    "budget_report",
    "compare_json_schemas",
    "estimate_tokens",
    "evaluate_golden_case",
    "extract_lineage_edges",
    "pack_context",
]
