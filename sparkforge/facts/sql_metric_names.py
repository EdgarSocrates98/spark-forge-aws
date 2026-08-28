"""Carregador do mapa canonico de nome de metrica SQL do Spark.

Fail-closed pelo mesmo motivo que `facts/cloudwatch_retention.py`: mapa que
some vira dicionario vazio, todo nome de metrica vira desconhecido, e a
extracao inteira sai sem uma unica measure -- sem erro nenhum. Silencio que
se parece com "esta execucao nao publicou metrica" e o pior modo de falha
possivel para este extrator, porque e indistinguivel do caso legitimo.

O mapa e LISTA FECHADA. Nome fora dele nao recebe palpite: quem chama recebe
`None` e emite a lacuna com o nome cru.

Caminho: `_MAP_PATH` vem de `knowledge_dir()` (`sparkforge.knowledge_ref`), o
mesmo helper que resolve `knowledge/` para todo o pacote -- variavel de
ambiente `SPARKFORGE_KNOWLEDGE`, depois raiz do repo, depois o fallback
embarcado ao lado do pacote quando instalado como wheel. Contar `parents[N]`
a mao aqui duplicaria essa resolucao e divergiria dela na primeira mudanca de
layout.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.knowledge_ref import knowledge_dir

_MAP_PATH: Path = knowledge_dir() / "spark" / "sql-metrics.yaml"

_CAMPOS = ("published", "measure", "metric_type", "verified_in")


class MetricMapError(RuntimeError):
    """O mapa nao pode ser lido ou nao tem a forma esperada."""


@lru_cache(maxsize=1)
def load_map() -> dict[str, dict[str, Any]]:
    """Devolve `{nome publicado: entrada}`. Levanta em vez de devolver vazio."""
    if not _MAP_PATH.is_file():
        raise MetricMapError(
            f"mapa de metricas SQL nao encontrado em {_MAP_PATH}. Ele e dado, nao "
            f"codigo: sem ele o extrator nao sabe qual nome vira qual measure."
        )
    try:
        cru = yaml.safe_load(_MAP_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MetricMapError(f"mapa de metricas SQL ilegivel: {exc}") from exc

    entradas = (cru or {}).get("metrics")
    if not isinstance(entradas, list) or not entradas:
        raise MetricMapError(
            f"{_MAP_PATH}: a chave `metrics` precisa ser uma lista nao vazia."
        )

    mapa: dict[str, dict[str, Any]] = {}
    for entrada in entradas:
        if not isinstance(entrada, dict) or any(c not in entrada for c in _CAMPOS):
            raise MetricMapError(
                f"{_MAP_PATH}: entrada sem os campos {_CAMPOS}: {entrada!r}"
            )
        nome = entrada["published"]
        if nome in mapa:
            raise MetricMapError(
                f"{_MAP_PATH}: nome publicado duplicado {nome!r}. Duas measures para o "
                f"mesmo nome tornaria a atribuicao dependente da ordem do arquivo."
            )
        mapa[nome] = entrada
    return mapa


def measure_for(published: str) -> str | None:
    """Nome da measure para um nome publicado, ou `None` se ele nao esta no mapa."""
    entrada = load_map().get(published)
    return entrada["measure"] if entrada else None
