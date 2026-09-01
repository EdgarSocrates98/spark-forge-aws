"""`ReleaseDescriptor` -- o que uma release E, com a recusa NOMEADA.

POR QUE ESTE MODULO MORA EM `sparkforge/migration/` E NAO EM `sparkforge/facts/`.

`facts/` e onde EXTRACAO mora: cada modulo de la le um artefato -- event log,
plano fisico, listagem de S3, Terraform -- e devolve fact. `runtime_matrix.py`
e a excecao ja aceita naquele pacote, porque carrega dado externo de
`knowledge/`, e e justamente dele que este modulo se alimenta. O que
`ReleaseDescriptor` faz nao e extrair de artefato nenhum: e COMPOR sobre facts
que outro verbo ja extraiu, que e a linha que o `CLAUDE.md` deste repositorio
desenha entre `analyze *` e os verbos de topo. Por a composicao dentro de
`facts/` apagaria essa linha no primeiro modulo que a atravessasse.

`migration/` e onde a pergunta vive. `version_path.py` ja responde "quais
degraus existem entre estas duas versoes" para o Glue, `assessment.py` julga
cada degrau, e o sub-projeto 3 -- `MigrationAssessment` para EMR -- e o
consumidor declarado deste modelo. Um descritor de release e o dado que falta
para aquele assessment existir sem inventar; ele nasce ao lado de quem vai
consumi-lo.

AS TRES REGRAS QUE ESTE MODULO EXISTE PARA NAO QUEBRAR.

1. COMPONENTE AUSENTE DA FONTE E RECUSA NOMEADA, nunca string vazia nem chave
   ausente em silencio. E a §20 do `CLAUDE.md`. E ha DUAS recusas diferentes,
   com nomes diferentes, porque elas destravam com medidas diferentes:

   `PLATFORM_DOES_NOT_PUBLISH`  a fonte daquela plataforma nao publica aquele
                                componente em release NENHUMA. `hadoop` no EMR
                                on EKS: 0 de 34 paginas. Destrava com uma fonte
                                nova, nao com uma leitura nova.
   `RELEASE_CELL_ABSENT`        a fonte publica o componente como eixo, e a
                                celula DAQUELA release nao esta la. `iceberg`
                                em `emr-6.4.0`, onde a celula da pagina oficial
                                e literalmente vazia; `java` em Glue 5.1, que
                                as outras quatro releases de Glue tem. Destrava
                                com uma leitura da pagina daquela release.

   Colapsar as duas num "nao sei" so faria o operador procurar no lugar errado.

2. NUNCA HERDAR VALOR DE OUTRA PLATAFORMA. O sub-projeto 1 mediu que as
   matrizes DIVERGEM: `emr-7.7.0` publica Iceberg `1.7.1-amzn-0` no EC2 e
   `1.6.1-amzn-2` no EKS, e Spark `3.5.3-amzn-1` contra `3.5.3-amzn-0`. Cada
   descritor le a matriz da SUA plataforma e nao consulta as outras. Nao ha
   fallback, nao ha "se faltar, pega do EC2".

3. `python_installed` DE EC2 E CONJUNTO, NAO VALOR. A pagina declara os
   interpretadores INSTALADOS (`2.7, 3.7` em 6.x). Achatar num valor so
   escolheria por conta propria qual deles o PySpark usa -- que e outra
   pergunta, e a AWS a responde numa coluna separada (`python`), so na serie
   7.x. `Component.is_set` distingue as duas, e `to_dict` emite lista onde a
   fonte publica conjunto.

O ROTULO. `release` sai como a matriz o INDEXA -- o numero solto para EMR e
Glue, e o rotulo inteiro para a familia `spark-8` do EMR --, e `describe` aceita
tambem a forma com o prefixo `emr-`, normalizada pela mesma conta de
`sparkforge/facts/runtime_detect._emr_key` que o resto do motor usa. A spec
pedia "o rotulo como a fonte publica", e as duas grafias sao publicadas -- a
pagina do EMR escreve `emr-7.7.0` no titulo e `7.7.0` na tabela. Uma chave so
e o que mantem o diff deterministico; duas grafias na saida dariam dois
descritores diferentes para a mesma release.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from sparkforge.facts import runtime_matrix as rm

# As quatro plataformas que este motor conhece, em ordem fixa.
PLATFORMS: tuple[str, ...] = ("glue", "emr_ec2", "emr_serverless", "emr_eks")

# Os dois nomes da recusa. Ver a regra 1 do docstring do modulo.
PLATFORM_DOES_NOT_PUBLISH = "platform_source_does_not_publish"
RELEASE_CELL_ABSENT = "release_cell_absent"
UNRESOLVED_KINDS: frozenset[str] = frozenset(
    {PLATFORM_DOES_NOT_PUBLISH, RELEASE_CELL_ABSENT}
)

# Componente que a fonte publica como CONJUNTO e nao como valor. Hoje um so.
_CONJUNTOS: frozenset[str] = frozenset({"python_installed"})

# Como a prosa nomeia cada plataforma nas mensagens de recusa.
_NOME_HUMANO: Mapping[str, str] = MappingProxyType(
    {
        "glue": "AWS Glue",
        "emr_ec2": "Amazon EMR on EC2",
        "emr_serverless": "Amazon EMR Serverless",
        "emr_eks": "Amazon EMR on EKS",
    }
)

# O diretorio de `knowledge/` de cada plataforma, citado na razao da recusa
# para que ela nomeie ONDE a medida que a destravaria teria de aparecer.
_KNOWLEDGE_DIR: Mapping[str, str] = MappingProxyType(
    {
        "glue": "knowledge/glue/",
        "emr_ec2": "knowledge/emr/",
        "emr_serverless": "knowledge/emr-serverless/",
        "emr_eks": "knowledge/emr-eks/",
    }
)

# `sources` e `retrieved` declaram procedencia da LINHA e nao sao componente.
# `_carrega_matriz_fechada` ja as filtra nas tres matrizes de EMR; `load()`
# (Glue) NAO as filtra -- a linha resolvida de Glue as devolve junto dos cinco
# componentes. Filtrar aqui e o que impede o descritor de inventar dois eixos
# em todas as cinco releases de Glue. Medido em 2026-08-31.
_RESERVADAS: frozenset[str] = frozenset({"sources", "retrieved"})


class ReleaseDescriptorError(ValueError):
    """Base das recusas deste modulo, para quem quiser capturar as duas."""


class UnknownPlatform(ReleaseDescriptorError):
    """Plataforma fora das quatro. Erro NOMEADO, com a lista das quatro."""


class UnknownRelease(ReleaseDescriptorError):
    """Release que aquela plataforma nao conhece.

    Erro nomeado e nao `KeyError` porque as matrizes tem fronteiras diferentes
    e um `KeyError` nao diz qual delas foi cruzada: `6.3.0` existe no EMR on
    EKS (que desce ate `5.32.0`) e nao no EC2 (que comeca em `6.4.0`), e
    `spark-8.0-preview` so existe no Serverless.
    """


@dataclass(frozen=True)
class Component:
    """Uma celula da matriz, com a procedencia que a sustenta.

    `version` e `str` para o caso comum e `tuple[str, ...]` quando a fonte
    publica CONJUNTO -- `is_set` diz qual dos dois, sem que o consumidor tenha
    de adivinhar por `isinstance`.
    """

    name: str
    version: str | tuple[str, ...]
    sources: tuple[str, ...]
    retrieved: str | None

    @property
    def is_set(self) -> bool:
        return isinstance(self.version, tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": list(self.version) if self.is_set else self.version,
            "is_set": self.is_set,
            "sources": list(self.sources),
            "retrieved": self.retrieved,
        }


@dataclass(frozen=True)
class Unresolved:
    """Uma recusa com nome, tipo e a medida que a destravaria."""

    component: str
    kind: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"component": self.component, "kind": self.kind, "reason": self.reason}


@dataclass(frozen=True)
class ReleaseDescriptor:
    """O que uma release e, segundo a fonte daquela plataforma e so ela."""

    platform: str
    release: str
    components: Mapping[str, Component]
    refused: Mapping[str, Unresolved]
    sources: tuple[str, ...]
    retrieved: str | None

    @property
    def unresolved(self) -> tuple[str, ...]:
        """Os componentes recusados, nomeados e ordenados.

        A spec pede `unresolved: [str]`, e e isto. `refused` carrega o tipo e a
        razao de cada um, porque a §20 do `CLAUDE.md` pede a recusa COM a medida
        que a destravaria -- uma lista de nomes sozinha diz que nao se sabe, e
        nao diz o que fazer a respeito.
        """
        return tuple(sorted(self.refused))

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "release": self.release,
            "components": {
                nome: componente.to_dict()
                for nome, componente in sorted(self.components.items())
            },
            "unresolved": list(self.unresolved),
            "unresolved_detail": {
                nome: self.refused[nome].to_dict() for nome in self.unresolved
            },
            "sources": list(self.sources),
            "retrieved": self.retrieved,
        }


def _publicados(platform: str) -> frozenset[str]:
    if platform == "glue":
        return rm.GLUE_COMPONENTS
    if platform == "emr_ec2":
        return rm.EMR_COMPONENTS
    if platform == "emr_serverless":
        return rm.EMR_SERVERLESS_COMPONENTS
    if platform == "emr_eks":
        return rm.EMR_EKS_COMPONENTS
    raise UnknownPlatform(_recusa_de_plataforma(platform))


def published_components(platform: str) -> frozenset[str]:
    """O que a fonte DAQUELA plataforma publica como eixo, em release alguma ou
    em todas. Nao e o que a release tem: e o que a fonte tem coluna para ter."""
    return _publicados(platform)


def _universo() -> tuple[str, ...]:
    uniao: set[str] = set()
    for plataforma in PLATFORMS:
        uniao |= _publicados(plataforma)
    return tuple(sorted(uniao))


# Todo componente que ALGUMA das quatro fontes publica. E o eixo comum contra o
# qual cada descritor declara o que tem e o que recusa -- derivado das quatro
# matrizes, nunca escrito a mao, para nao poder divergir delas.
COMPONENT_UNIVERSE: tuple[str, ...] = _universo()


def _matriz(platform: str) -> dict[str, dict[str, Any]]:
    if platform == "glue":
        return rm.load()
    if platform == "emr_ec2":
        return rm.load_emr()
    if platform == "emr_serverless":
        return rm.load_emr_serverless()
    if platform == "emr_eks":
        return rm.load_emr_eks()
    raise UnknownPlatform(_recusa_de_plataforma(platform))


def _procedencia(platform: str) -> dict[str, dict[str, Any]]:
    if platform == "glue":
        return rm.release_provenance()
    if platform == "emr_ec2":
        return rm.emr_release_provenance()
    if platform == "emr_serverless":
        return rm.emr_serverless_release_provenance()
    if platform == "emr_eks":
        return rm.emr_eks_release_provenance()
    raise UnknownPlatform(_recusa_de_plataforma(platform))


def _recusa_de_plataforma(platform: str) -> str:
    return (
        f"plataforma {platform!r} fora das quatro que este motor conhece: "
        f"{', '.join(PLATFORMS)}"
    )


def _normaliza(platform: str, release: str) -> str:
    """`emr-7.7.0` e `7.7.0` sao a mesma release; a chave da matriz e a segunda.

    A mesma conta de `sparkforge/facts/runtime_detect._emr_key`, repetida aqui
    em vez de importada porque aquela funcao e privada do modulo de deteccao e
    importa-la acoplaria o descritor ao caminho quente da deteccao de runtime.
    A conta e uma linha; o acoplamento seria permanente. Glue nao usa prefixo,
    e por isso a normalizacao nao se aplica a ele.
    """
    texto = str(release).strip()
    if platform == "glue":
        return texto
    return texto[4:] if texto.lower().startswith("emr-") else texto


def normalize_release(platform: str, release: str) -> str:
    """A grafia UNICA de uma release, aceitando as duas que a fonte publica.

    Publica porque `version_path` precisa da MESMA conta para que o degrau que
    ele emite seja conferivel contra `known_releases()` sem traducao no meio --
    duas normalizacoes independentes divergiriam no primeiro caso de borda, e o
    caso de borda aqui e um prefixo de tres letras.
    """
    if platform not in PLATFORMS:
        raise UnknownPlatform(_recusa_de_plataforma(platform))
    return _normaliza(platform, release)


def platform_label(platform: str) -> str:
    """O nome da plataforma como a prosa a escreve (`Amazon EMR on EC2`).

    Publica pela mesma razao de `normalize_release`: a declaracao de cobertura
    de `MigrationAssessment` nomeia a plataforma para o operador, e uma segunda
    tabela de nomes divergiria desta na primeira plataforma nova.
    """
    if platform not in PLATFORMS:
        raise UnknownPlatform(_recusa_de_plataforma(platform))
    return _NOME_HUMANO[platform]


def known_releases(platform: str) -> tuple[str, ...]:
    """As releases que aquela plataforma conhece, na ordem em que o YAML as
    declara -- que e a ordem editorial da fonte (mais nova primeiro), e nao uma
    ordem semantica de versao. Ordenar aqui exigiria um comparador que
    entendesse `spark-8.0-preview`, e nao ha consumidor que peca isso."""
    return tuple(_matriz(platform))


def _componente(
    nome: str,
    valor: Any,
    fontes_da_release: tuple[str, ...],
    retrieved_da_release: str | None,
    evidencia: Mapping[str, Any] | None,
) -> Component:
    """Monta a celula, preferindo a procedencia MAIS especifica que existir.

    A forma longa do Glue (`status` + `claims`) declara fonte e data POR CLAIM,
    e essa e a procedencia mais fina que este repositorio tem -- `python` de
    Glue 6.0 tem tres claims, tres fontes e a data em que cada uma foi lida.
    Quando ela existe, ela vence a da release; quando nao existe, a da release
    responde. Nunca as duas somadas: seriam duas leituras diferentes do mesmo
    numero apresentadas como uma.
    """
    registro = (evidencia or {}).get(nome)
    if isinstance(registro, dict) and registro.get("claims"):
        vistas: dict[str, None] = {}
        datas: list[str] = []
        for claim in registro["claims"]:
            vistas.setdefault(str(claim["source"]), None)
            datas.append(str(claim["retrieved"]))
        return Component(
            name=nome,
            version=valor,
            sources=tuple(vistas),
            retrieved=max(datas) if datas else retrieved_da_release,
        )
    versao = tuple(str(v) for v in valor) if nome in _CONJUNTOS else str(valor)
    return Component(
        name=nome,
        version=versao,
        sources=fontes_da_release,
        retrieved=retrieved_da_release,
    )


def _razao_plataforma(platform: str, componente: str) -> str:
    return (
        f"a fonte do {_NOME_HUMANO[platform]} nao publica `{componente}` em release "
        f"nenhuma -- ele nao e coluna daquela matriz. Destrava com uma FONTE nova "
        f"que publique `{componente}` por release, declarada em "
        f"{_KNOWLEDGE_DIR[platform]}runtime-matrix.yaml e em "
        f"knowledge/sources.lock.json; nao destrava copiando o valor de outra "
        f"plataforma, que e o que o sub-projeto 1 mediu divergir"
    )


def _razao_celula(platform: str, componente: str, release: str) -> str:
    return (
        f"a fonte do {_NOME_HUMANO[platform]} publica `{componente}` como eixo, e a "
        f"celula de `{release}` nao esta la. Destrava com a LEITURA da pagina daquela "
        f"release, acrescentando a celula em {_KNOWLEDGE_DIR[platform]}"
        f"runtime-matrix.yaml com `sources` e `retrieved` proprios"
    )


def describe(platform: str, release: str) -> ReleaseDescriptor:
    """O descritor de uma release, lido da matriz daquela plataforma e so dela.

    `platform` e uma das quatro de `PLATFORMS`; `release` e o rotulo com ou sem
    o prefixo `emr-`. Plataforma ou release fora do conhecido levantam
    `UnknownPlatform`/`UnknownRelease` com a lista do que e conhecido -- nunca
    `KeyError`, que nao diz qual fronteira foi cruzada.
    """
    if platform not in PLATFORMS:
        raise UnknownPlatform(_recusa_de_plataforma(platform))
    chave = _normaliza(platform, release)
    matriz = _matriz(platform)
    if chave not in matriz:
        conhecidas = ", ".join(known_releases(platform))
        raise UnknownRelease(
            f"release {release!r} (chave {chave!r}) fora da matriz de {platform}; "
            f"conhecidas: {conhecidas}"
        )

    procedencia = _procedencia(platform).get(chave, {})
    fontes = tuple(procedencia.get("sources") or ())
    retrieved = procedencia.get("retrieved")
    evidencia = rm.evidence().get(chave) if platform == "glue" else None
    publicados = _publicados(platform)

    linha = {
        nome: valor
        for nome, valor in matriz[chave].items()
        if nome not in _RESERVADAS
    }
    componentes = {
        nome: _componente(nome, valor, fontes, retrieved, evidencia)
        for nome, valor in sorted(linha.items())
    }
    recusados = {}
    for nome in COMPONENT_UNIVERSE:
        if nome in componentes:
            continue
        if nome in publicados:
            recusados[nome] = Unresolved(
                component=nome,
                kind=RELEASE_CELL_ABSENT,
                reason=_razao_celula(platform, nome, chave),
            )
        else:
            recusados[nome] = Unresolved(
                component=nome,
                kind=PLATFORM_DOES_NOT_PUBLISH,
                reason=_razao_plataforma(platform, nome),
            )
    return ReleaseDescriptor(
        platform=platform,
        release=chave,
        components=MappingProxyType(componentes),
        refused=MappingProxyType(recusados),
        sources=fontes,
        retrieved=retrieved,
    )


def describe_all(platform: str | None = None) -> tuple[ReleaseDescriptor, ...]:
    """Todos os descritores de uma plataforma, ou das quatro. O que os testes de
    invariante rodam sobre as 95 releases em vez de sobre amostra."""
    plataformas = PLATFORMS if platform is None else (platform,)
    return tuple(
        describe(p, release) for p in plataformas for release in known_releases(p)
    )
