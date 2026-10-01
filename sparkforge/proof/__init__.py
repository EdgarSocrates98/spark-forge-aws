"""Change Proof (§20): obrigacoes de prova de uma mudanca aplicada.

Para cada recomendacao que o operador aplicou, a prova deriva as obrigacoes dos
eixos que a regra declara em `action.moves` e da propria regra (resolucao), e
da a cada uma um desfecho: `refuted`, `not_refuted`, `inconclusive` ou
`unproven`. Nunca "provado": proxy de `funcval` e delta de `benchmark` nao
provam equivalencia nem melhoria atribuivel.

Este pacote nao le arquivo de facts nem roda o `judge`: recebe o que o adapter
ja leu e julgou. Nao importa `adapters` nem provider.
"""
from sparkforge.proof.axes import POLICY_FILE, PolicyError, load_policy, validate_policy
from sparkforge.proof.keys import stable_key
from sparkforge.proof.prove import OUTCOMES, REFUSED, kinds_in_when, prove, select_applied

__all__ = [
    "OUTCOMES",
    "POLICY_FILE",
    "REFUSED",
    "PolicyError",
    "kinds_in_when",
    "load_policy",
    "prove",
    "select_applied",
    "stable_key",
    "validate_policy",
]
