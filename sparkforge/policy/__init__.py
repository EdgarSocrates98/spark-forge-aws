"""Politica de seguranca declarada (§16): `.sparkforge/policy.yaml`.

Uma fonte, tres portas: o servidor MCP (via `CallPolicy`), o hook `PreToolUse`
do Claude Code (`python -m sparkforge.policy.hook`, so `deny`) e as regras
`permissions.ask` geradas no `.claude/settings.json` (`ask`).

Este pacote NAO importa `sparkforge.adapters` no caminho do hook: o hook roda
em todo Bash, e importar o catalogo de tools custa ~0,5 s (medido 2026-09-13).
"""
from sparkforge.policy.decide import ALLOW, ASK, DENY, Decisao, decidir_bash, decidir_caminho
from sparkforge.policy.load import POLICY_RELATIVE, PolicyError, Politica, Regra, carregar

__all__ = [
    "ALLOW",
    "ASK",
    "DENY",
    "POLICY_RELATIVE",
    "Decisao",
    "Politica",
    "PolicyError",
    "Regra",
    "carregar",
    "decidir_bash",
    "decidir_caminho",
]
