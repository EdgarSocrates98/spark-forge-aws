"""Escolha de capacidade sob restricao de SLA.

NAO e um extrator. Escolher capacidade e juizo, e fact nao julga -- mesmo
molde de `sparkforge/workload/`. Toda recomendacao nasce `REVIEW`, e nada
neste pacote aplica mudanca nenhuma.
"""
from sparkforge.capacity.plan import Candidate, CapacityPlan, build_capacity_plan

__all__ = ["Candidate", "CapacityPlan", "build_capacity_plan"]
