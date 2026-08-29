"""Carrega a retencao de metrica do CloudWatch como dado com data e fonte.

POR QUE ESTE MODULO NAO FIXA NUMERO. `collect_cloudwatch` consultava com
`Period: 30` fixo, e ponto de granularidade sub-minuto sobrevive poucas horas
no CloudWatch. A mesma query sobre um run de vinte dias atras devolve serie
vazia, e vazio se parece com observabilidade desligada no job -- causa
diferente, remedio diferente.

Derivar o periodo da idade do run exige a tabela de retencao, e a tabela
precisa vir de `knowledge/glue/observability.yaml`, com fonte e data, pela
mesma razao de `sparkforge/facts/pricing.py`: numero envelhecido nao parece
errado, parece preciso.

Fail-closed no mesmo molde: entrada sem `source`, `source_type` ou `retrieved`
carregaria em silencio e viraria, tres saltos adiante, uma query que devolve
vazio sem ninguem saber por que.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from sparkforge.facts.runtime_matrix import SOURCE_TYPES
from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file

_ARQUIVO = "glue/observability.yaml"
_CAMPOS_DE_EVIDENCIA = ("source", "source_type", "retrieved")
_CAMPOS_DE_RETENCAO = ("period_seconds", "retention_days")


class RetentionError(ValueError):
    """Tabela de retencao ausente, vazia ou com entrada sem evidencia."""


def _validar(indice: int, entrada: Any) -> None:
    rotulo = f"retention[{indice}]"
    if not isinstance(entrada, dict):
        raise RetentionError(
            f"{rotulo}: entrada precisa ser um mapa, veio {type(entrada).__name__}"
        )
    for campo in _CAMPOS_DE_RETENCAO:
        valor = entrada.get(campo)
        if not isinstance(valor, int) or valor <= 0:
            raise RetentionError(f"{rotulo}: {campo} precisa ser inteiro positivo, veio {valor!r}")
    for campo in _CAMPOS_DE_EVIDENCIA:
        if not entrada.get(campo):
            raise RetentionError(
                f"{rotulo}: sem {campo}. Retencao sem procedencia carrega em silencio e "
                f"vira uma query que devolve vazio sem razao declarada"
            )
    if entrada["source_type"] not in SOURCE_TYPES:
        raise RetentionError(
            f"{rotulo}: source_type {entrada['source_type']!r} fora de {sorted(SOURCE_TYPES)}"
        )


@lru_cache(maxsize=1)
def retention_table() -> tuple[dict[str, Any], ...]:
    """A tabela lida do YAML, ordenada por periodo crescente."""
    caminho = safe_knowledge_file(knowledge_dir(), _ARQUIVO)
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    entradas = dados.get("retention") or []
    if not entradas:
        raise RetentionError(f"{_ARQUIVO}: lista `retention` ausente ou vazia")
    for indice, entrada in enumerate(entradas):
        _validar(indice, entrada)
    return tuple(sorted(entradas, key=lambda e: e["period_seconds"]))


def period_for_age_days(age_days: float) -> int | None:
    """O menor periodo cuja retencao ainda cobre um ponto com esta idade.

    Menor periodo primeiro porque granularidade mais fina e sempre preferivel
    enquanto o dado existe. `None` diz que nenhum periodo cobre -- o ponto
    expirou em todas as granularidades, e quem chamar precisa dizer isso em vez
    de consultar e receber vazio.
    """
    if age_days < 0:
        raise ValueError(f"idade negativa: {age_days}")
    for entrada in retention_table():
        if age_days <= entrada["retention_days"]:
            return int(entrada["period_seconds"])
    return None
