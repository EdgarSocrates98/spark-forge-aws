"""Expande um par origem/alvo nos degraus intermediarios da matriz.

POR QUE ISSO EXISTE SEPARADO DO PLANO DE EXECUCAO: o §6.2 do prompt de migracao
distingue migracao direta OPERACIONAL de analise CUMULATIVA obrigatoria. Quem
migra pode saltar 4.0 para 6.0 num movimento so; quem ANALISA nao pode, porque
os breaking changes se acumulam degrau a degrau e um salto esconde os do meio.

O modulo nao conhece regra, fact nem finding. Ele responde uma pergunta so:
quais degraus existem entre estas duas versoes, segundo a matriz.
"""
from __future__ import annotations

from sparkforge.facts import runtime_matrix


def steps(source: str, target: str) -> list[tuple[str, str]]:
    conhecidas = runtime_matrix.known_versions()
    for versao in (source, target):
        if versao not in conhecidas:
            raise ValueError(
                f"versao {versao!r} fora da matriz; conhecidas: {', '.join(conhecidas)}"
            )
    inicio = conhecidas.index(source)
    fim = conhecidas.index(target)
    if fim < inicio:
        raise ValueError(f"alvo anterior a origem: {source!r} -> {target!r}")
    return [(conhecidas[i], conhecidas[i + 1]) for i in range(inicio, fim)]
