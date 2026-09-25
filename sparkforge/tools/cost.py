"""Estimativa de custo em token.

`estimate_tokens` e heuristica -- 4 caracteres por token -- e nao substitui a
contagem do provedor. Todo retorno carrega `is_estimate: True` para que nenhum
consumidor trate o numero como medicao.

A funcao e a de `sparkforge.agents.budget`, reexportada pelo mesmo nome porque
`sparkforge.tools` a publica e `sparkforge/tools/cli.py` a chama: uma definicao so,
e `is` prova que e a mesma.
"""

from sparkforge.agents.budget import estimate_tokens

__all__ = ["budget_report", "estimate_tokens"]


def budget_report(messages, limit=12000):
    text = " ".join(str(m.get("content", m.get("text", ""))) for m in messages)
    estimated = estimate_tokens(text)
    return {
        "estimated_tokens": estimated,
        "limit": limit,
        "remaining": max(0, limit - estimated),
        "within_budget": estimated <= limit,
        "is_estimate": True,
    }
