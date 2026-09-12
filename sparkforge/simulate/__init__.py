"""Simulate (§19): o que uma mudanca de configuracao move, estruturalmente.

`--set <camada>:<chave>=<valor>` altera o valor de facts de configuracao que ja
existem; os dois lados passam pelo mesmo pipeline (tirar derivados, rederivar,
detectar o runtime, julgar) e a comparacao diz o que some e o que aparece.
Nenhuma medida e prevista: spill e tempo nao sao fact de configuracao.

Este pacote nao le arquivo nem roda o `judge`: o adapter faz as duas coisas.
"""
from sparkforge.simulate.diff import DERIVED_KINDS, diff, strip_derived
from sparkforge.simulate.layers import CAMADAS
from sparkforge.simulate.patch import Mudanca, SimulateError, apply_sets, parse_sets

REFUSED: tuple[dict[str, str], ...] = (
    {"field": "performance_prediction", "reason": "spill_e_tempo_nao_sao_fact_de_configuracao"},
    {"field": "dependency_incompatibility", "reason": "use_sparkforge_migration_assess"},
    {"field": "execution_graph", "reason": "nao_e_previsivel_a_partir_de_configuracao"},
)

__all__ = [
    "CAMADAS",
    "DERIVED_KINDS",
    "REFUSED",
    "Mudanca",
    "SimulateError",
    "apply_sets",
    "diff",
    "parse_sets",
    "strip_derived",
]
