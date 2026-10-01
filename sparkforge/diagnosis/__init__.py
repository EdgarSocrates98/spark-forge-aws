"""Composicao sobre findings ja julgados. NAO le artefato e NAO julga nada novo.

Este pacote existe para uma pergunta que o `judge` nao responde: "das coisas que
dispararam, por onde eu comeco, e o que eu NAO sei?". `judge` devolve uma lista
plana de achados em ordem deterministica; ordenar por consequencia e nomear a
lacuna sao duas operacoes DEPOIS dele, e nenhuma delas produz achado novo.

Ele e do mesmo genero dos verbos de topo descritos no `CLAUDE.md` -- `workload`,
`capacity`, `finops`, `arbitrate`: compoe sobre facts e findings que outro verbo
extraiu, e por isso nao e um `analyze`.
"""
from __future__ import annotations

from sparkforge.diagnosis.root_cause import (
    ORDEM_DE_SEVERIDADE,
    rank_root_causes,
)

__all__ = ["rank_root_causes", "ORDEM_DE_SEVERIDADE"]
