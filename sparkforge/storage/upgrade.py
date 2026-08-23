"""Cruza o inventario DECLARADO de consumidores com a matriz de features.

O QUE ESTE MODULO RESPONDE, e o que ele nunca faz. A pergunta e a secao 24 e a
secao 25 do prompt na mesma frase: "posso subir esta tabela para format v3?".
A resposta sai de duas fontes que ja existiam separadas -- `env.consumer`
(`sparkforge/facts/consumers.py`), que diz QUEM le a tabela, e
`knowledge/storage/iceberg-feature-support.yaml`, que diz o que cada engine
suporta, uma celula por par, com fonte. Nada cruzava as duas, e por isso nada
impedia recomendar v3 para quem tem Athena consumindo.

NUNCA EXECUTA O UPGRADE. A secao 94 e explicita, e a garantia aqui e
estrutural, nao textual: o modulo nao importa cliente de AWS, nao importa
Spark, nao roda subprocesso. Ele le uma matriz de conhecimento e devolve um
veredito -- `tests/test_storage_upgrade.py::TestNuncaExecuta` mede isso pela
fonte do proprio modulo.

POR QUE ISTO NAO E UMA REGRA DO CATALOGO. O padrao do repositorio e julgar no
catalogo, e ele foi tentado primeiro. O avaliador de `expr`
(`rules/catalog/README.md`, secao "Avaliador de `expr`") tem whitelist de nos
AST sem `Call` e sem `In`, e `where` compara igualdade -- nao existe forma de
escrever "servico que a matriz nao declara suportado" numa condicao. A
alternativa seria uma regra por engine, cada uma repetindo em YAML o que a
matriz ja diz com fonte e `retrieved`; a matriz existe precisamente porque
suporte e dado com procedencia e versao, e copia-lo para o catalogo o faria
divergir na primeira atualizacao de fonte.

E POR QUE ISSO NAO DUPLICA `SF-ENV-002`. Aquela regra continua sendo o achado
P0 do caso documentado (tabela v3 lida por Athena, com o erro textual "Cannot
read unsupported version 3"). Este modulo nao emite `Finding` nenhum: ele
alimenta um GATE. Um caso de Athena com tabela v3 produz um achado -- o da
regra -- e um gate fechado, nunca dois achados para o mesmo problema.

O VOCABULARIO DE VEREDITO, e a ordem de precedencia entre eles. `BLOCKED`
vence `UNRESOLVED` porque ja existe fonte dizendo nao: nao ha o que resolver.
`UNRESOLVED` vence `CONDITIONAL` e `SAFE` porque desconhecimento nao pode ser
absorvido por uma celula boa de outra engine -- a resposta honesta de "nao ha
fonte sobre o PyIceberg" nao e "seguro".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sparkforge.storage import feature_support

# Fechado, e na ordem de precedencia -- do pior desfecho para o melhor.
VERDICTS = ("BLOCKED", "UNRESOLVED", "CONDITIONAL", "SAFE")

# Status de celula que fecha a decisao: a fonte diz que a engine nao executa.
_BLOQUEIA = frozenset({"UNSUPPORTED"})

# Status que nao bloqueia mas tambem nao libera sem que alguem leia a nota da
# celula. `CONFLICTING` entra aqui de proposito: duas fontes incompativeis e
# uma condicao a resolver por leitura, nao um desconhecimento a coletar.
_CONDICIONA = frozenset({"PARTIAL", "READ_ONLY", "WRITE_ONLY", "PREVIEW", "CONFLICTING"})


@dataclass(frozen=True)
class SupportCell:
    """Uma celula da matriz, com a coordenada que a identifica."""

    feature: str
    engine: str
    engine_version: str
    status: str
    source: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "status": self.status,
            "source": self.source,
            "note": self.note,
        }


@dataclass
class UpgradeAssessment:
    """O veredito, e as celulas que o sustentam.

    `cells` nao e resumo: e a lista das celulas consultadas, cada uma com a
    fonte. Um veredito sem as celulas seria uma palavra que ninguem consegue
    conferir, e a matriz existe justamente para que suporte seja conferivel.
    """

    consumers: list[str]
    target_spec_version: int
    verdict: str
    cells: list[SupportCell] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consumers": list(self.consumers),
            "target_spec_version": self.target_spec_version,
            "verdict": self.verdict,
            "cells": [c.to_dict() for c in self.cells],
            "unresolved": list(self.unresolved),
        }


def _features_da_spec(target_spec_version: int) -> list[str]:
    return sorted(
        nome
        for nome, dados in feature_support.load().items()
        if dados.get("spec_version") == target_spec_version
    )


def assess_upgrade(consumers: list[str], target_spec_version: int) -> UpgradeAssessment:
    """Veredito de subir para `target_spec_version` dado quem consome.

    `consumers` sao nomes de engine no vocabulario de
    `sparkforge/facts/consumers.py:KNOWN_SERVICES`. Um nome fora da matriz nao
    e erro: ele cai em `UNKNOWN`, que e a resposta certa -- ninguem coletou
    fonte sobre ele.

    Inventario VAZIO devolve `UNRESOLVED`, nunca `SAFE`. Ausencia de
    declaracao nao e declaracao de ausencia: um job sem inventario nao e um job
    sem consumidor, e responder "seguro" ali seria a resposta errada com cara
    de resposta certa.
    """
    if target_spec_version not in feature_support.SPEC_VERSIONS:
        raise ValueError(
            f"versao de spec {target_spec_version!r} fora de "
            f"{sorted(feature_support.SPEC_VERSIONS)}"
        )

    features = _features_da_spec(target_spec_version)
    consultadas: list[SupportCell] = []
    nao_resolvido: list[str] = []

    for engine in sorted(set(consumers)):
        for feature in features:
            celula = feature_support.cell(feature, engine)
            consultadas.append(
                SupportCell(
                    feature=feature,
                    engine=engine,
                    # A fonte pode nao qualificar por versao de engine; repetir
                    # a chave curinga e mais honesto que inventar um numero.
                    engine_version=feature_support.ANY_VERSION,
                    status=celula["status"],
                    source=celula.get("source", ""),
                    note=celula.get("note", ""),
                )
            )
            if celula["status"] == "UNKNOWN":
                nao_resolvido.append(
                    f"{engine}: nenhuma fonte sobre `{feature}` -- a matriz tem "
                    f"UNKNOWN, e UNKNOWN e desconhecimento declarado, nao ausencia "
                    f"de risco"
                )

    if not consumers:
        return UpgradeAssessment(
            consumers=[],
            target_spec_version=target_spec_version,
            verdict="UNRESOLVED",
            cells=[],
            unresolved=[
                "nenhum consumidor declarado -- sem inventario nao ha quem "
                "consultar, e ausencia de declaracao nao e declaracao de "
                "ausencia; declare em `.sparkforge/consumers.yaml`"
            ],
        )

    if any(c.status in _BLOQUEIA for c in consultadas):
        veredito = "BLOCKED"
    elif nao_resolvido:
        veredito = "UNRESOLVED"
    elif any(c.status in _CONDICIONA for c in consultadas):
        veredito = "CONDITIONAL"
    else:
        veredito = "SAFE"

    return UpgradeAssessment(
        consumers=sorted(set(consumers)),
        target_spec_version=target_spec_version,
        verdict=veredito,
        cells=consultadas,
        unresolved=nao_resolvido,
    )
