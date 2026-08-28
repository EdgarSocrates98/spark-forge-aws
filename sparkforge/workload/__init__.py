"""Perfil de workload: os eixos, e a confianca de cada um.

NAO e um extrator. Extrator emite fact, e fact nunca aplica limiar -- dizer que
`scan` e `extreme` e exatamente aplicar limiar. Este pacote e o mecanismo
proprio de julgamento, no molde de `MigrationAssessment` e do `benchmark`, que
tambem nao cabem em regra do catalogo e tambem declaram o que garantem.
"""
from sparkforge.workload.axis import Axis, unknown_axis

__all__ = ["Axis", "unknown_axis"]
