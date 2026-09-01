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

from sparkforge.storage import feature_support, readiness

# Fechado, e na ordem de precedencia -- do pior desfecho para o melhor.
VERDICTS = ("BLOCKED", "UNRESOLVED", "CONDITIONAL", "SAFE")

# Status de celula que fecha a decisao: a fonte diz que a engine nao executa.
_BLOQUEIA = frozenset({"UNSUPPORTED"})

# Status que nao bloqueia mas tambem nao libera sem que alguem leia a nota da
# celula. `CONFLICTING` entra aqui de proposito: duas fontes incompativeis e
# uma condicao a resolver por leitura, nao um desconhecimento a coletar.
# `ENGINE_DEPENDENT` e `VERSION_DEPENDENT` entram pela mesma razao: as duas sao
# "depende de algo que voce ainda nao me disse", e isso e condicao a resolver,
# nunca liberacao.
_CONDICIONA = frozenset(
    {
        "PARTIAL",
        "READ_ONLY",
        "WRITE_ONLY",
        "PREVIEW",
        "CONFLICTING",
        "ENGINE_DEPENDENT",
        "VERSION_DEPENDENT",
    }
)

# Nomes que o `ConsumerGraph` reconhece e que a matriz NAO tem como responder,
# porque cada um responde por mais de uma coisa que diverge. Mapeia para o que
# o operador precisa declarar no lugar.
#
# `emr` e o unico hoje, e ele e o motivo desta entrega: as tres plataformas
# publicam Iceberg diferente em 6 de 26 releases comparaveis. Responder "EMR"
# e responder errado para pelo menos uma das tres, sem dizer qual.
AMBIGUOUS_SERVICES: dict[str, tuple[str, ...]] = {"emr": readiness.EMR_PLATFORMS}


@dataclass(frozen=True)
class SupportCell:
    """Uma celula da matriz, com a coordenada que a identifica."""

    feature: str
    engine: str
    engine_version: str
    status: str
    source: str = ""
    note: str = ""
    # Preenchidos so quando o operador declarou a release do consumidor e a
    # plataforma tem matriz de runtime. Vazios, dizem que o veredito daquela
    # celula veio da engine sem recorte de versao -- que e resposta mais fraca,
    # e nao resposta errada.
    reason: str = ""
    library_version: str = ""
    min_library_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "status": self.status,
            "source": self.source,
            "note": self.note,
            "reason": self.reason,
            "library_version": self.library_version,
            "min_library_version": self.min_library_version,
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
    # Consumidor DECLARADO pelo operador que a matriz nao avaliou -- nao tem
    # linha nenhuma nela. Sai em campo proprio porque a diferenca entre "a
    # matriz tem a linha e nao ha fonte" e "ninguem abriu a linha" desaparece
    # se as duas so aparecerem como `UNKNOWN` no meio das celulas.
    unevaluated_consumers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consumers": list(self.consumers),
            "target_spec_version": self.target_spec_version,
            "verdict": self.verdict,
            "cells": [c.to_dict() for c in self.cells],
            "unresolved": list(self.unresolved),
            "unevaluated_consumers": list(self.unevaluated_consumers),
        }


def _features_da_spec(target_spec_version: int) -> list[str]:
    return sorted(
        nome
        for nome, dados in feature_support.load().items()
        if dados.get("spec_version") == target_spec_version
    )


def _lacuna_nomeada(engine: str) -> str:
    """A frase de um consumidor DECLARADO que a matriz nao avaliou.

    Silencio aqui seria a pior saida possivel: o operador declarou o consumidor,
    e nao receber nada de volta se le como "esta bem". `SUPPORTED` por omissao
    seria pior ainda. A frase precisa dizer as duas coisas -- que ninguem
    avaliou, e qual medida destravaria.
    """
    alternativas = AMBIGUOUS_SERVICES.get(engine)
    if alternativas:
        return (
            f"{engine}: consumidor declarado e AMBIGUO -- as tres plataformas "
            f"publicam Iceberg diferente (em `emr-7.7.0` o EC2 traz 1.7.1-amzn-0 "
            f"e o EKS traz 1.6.1-amzn-2), entao uma resposta unica estaria errada "
            f"para pelo menos uma delas. Declare "
            f"{', '.join(f'`{a}`' for a in alternativas)} em "
            f"`.sparkforge/consumers.yaml`, com `release:` quando souber"
        )
    return (
        f"{engine}: consumidor declarado e AUSENTE da matriz -- nenhuma celula "
        f"foi avaliada para ele, o que e diferente de ter sido avaliado e dado "
        f"UNKNOWN. A medida que destrava: uma fonte da propria engine sobre a "
        f"feature, registrada em `knowledge/storage/iceberg-feature-support.yaml`"
    )


def assess_upgrade(
    consumers: list[str],
    target_spec_version: int,
    releases: dict[str, str] | None = None,
) -> UpgradeAssessment:
    """Veredito de subir para `target_spec_version` dado quem consome.

    `consumers` sao nomes de engine no vocabulario de
    `sparkforge/facts/consumers.py:KNOWN_SERVICES`.

    `releases` mapeia engine -> release label declarada pelo operador (`emr_eks`
    -> `emr-7.7.0`). E OPCIONAL, e a ausencia dele nao inventa nada: sem
    release, a celula consultada e a da engine sem recorte de versao. Com
    release, `sparkforge/storage/readiness.py` cruza a versao de Iceberg daquela
    release com o minimo de biblioteca da feature -- que e o unico jeito de a
    resposta diferir entre `emr_ec2` e `emr_eks` na MESMA release, como as
    fontes dizem que ela difere.

    CONSUMIDOR SEM LINHA NA MATRIZ NAO CAI EM SILENCIO. Ele sai em
    `unevaluated_consumers` e com uma frase propria em `unresolved`: "a matriz
    tem a linha e nao ha fonte" e "ninguem abriu a linha" sao dois
    desconhecimentos diferentes, e o segundo e o unico que uma pessoa consegue
    consertar.

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
    declaradas = feature_support.engines()
    releases = releases or {}
    consultadas: list[SupportCell] = []
    nao_resolvido: list[str] = []
    nao_avaliados: list[str] = []

    for engine in sorted(set(consumers)):
        if engine not in declaradas:
            nao_avaliados.append(engine)
            nao_resolvido.append(_lacuna_nomeada(engine))
        release = releases.get(engine, "")
        for feature in features:
            celula = feature_support.cell(feature, engine)
            if release:
                cruzada = readiness.readiness(feature, engine, release)
                consultadas.append(
                    SupportCell(
                        feature=feature,
                        engine=engine,
                        engine_version=release,
                        status=cruzada["status"],
                        source=cruzada["source"],
                        note=cruzada["note"],
                        reason=cruzada["reason"],
                        library_version=cruzada["library_version"],
                        min_library_version=cruzada["min_library_version"],
                    )
                )
                status = cruzada["status"]
                if status == "UNKNOWN":
                    nao_resolvido.append(
                        f"{engine} em `{release}`: `{feature}` fica UNKNOWN por "
                        f"`{cruzada['reason']}` -- ver a razao em "
                        f"`sparkforge/storage/readiness.py:REASONS`"
                    )
                continue
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
            if celula["status"] == "UNKNOWN" and engine in declaradas:
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
        unevaluated_consumers=nao_avaliados,
    )
