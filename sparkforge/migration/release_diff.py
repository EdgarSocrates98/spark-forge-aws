"""`ReleaseDiff` -- o que mudou entre dois descritores, com o EIXO declarado.

O EIXO, E POR QUE ELE E OBRIGATORIO NA SAIDA (D-4 da spec).

Comparar `emr-6.15.0` com `emr-7.5.0` na mesma plataforma e eixo `release`.
Comparar `emr-7.7.0` no EC2 com o MESMO rotulo no EKS e eixo `platform` -- e e
comparacao legitima: e onde mora o achado do sub-projeto 1, que o mesmo rotulo
publica Iceberg `1.7.1-amzn-0` num e `1.6.1-amzn-2` no outro. O que nao e
legitimo e somar os dois: apresentar "Iceberg mudou de 1.6.1 para 1.7.1" sem
dizer que a mudanca e de PLATAFORMA inverte a causa, e faz o operador procurar
num changelog de release uma diferenca que nunca esteve la.

`axis` e a tupla das dimensoes que EFETIVAMENTE variam entre os dois lados, em
ordem fixa (`platform` antes de `release`, da mais grossa para a mais fina).
Uma release contra ela mesma sai com `axis: ()` -- nada varia, e nada e
atribuivel a nada.

OS DOIS EIXOS AO MESMO TEMPO: EMITIR DECLARANDO OS DOIS, E RECUSAR A ATRIBUICAO.

Plataformas diferentes E releases diferentes e diff de dois eixos. Recusar
seria defensavel, e foi considerado; nao foi o escolhido, e a razao e medida:
"estou em `emr-6.15.0` no EC2 e vou para `emr-7.5.0` no EKS" e a pergunta
literal de uma migracao real, e recusa-la deixaria o operador sem a unica
resposta que a matriz sustenta -- os numeros dos dois lados -- para proteger uma
inferencia que ele nao pediu. O que NAO tem base nesse caso e a ATRIBUICAO:
nenhuma linha de `changed` pode ser creditada a release ou a plataforma
isoladamente. Entao a atribuicao e que sai em `unresolved`, por nome, com a
medida que a destrava (dois diffs de um eixo cada). Emitir calado seria a
terceira saida, e e a unica que nao esta disponivel.

`ADDED`/`REMOVED` NAO SAO O MESMO QUE "A PLATAFORMA PASSOU A EMBARCAR".

Este verbo le matriz de versao, e matriz de versao mede O QUE A FONTE PUBLICA.
Quando `python` aparece em `emr-7.0.0` e nao em `emr-6.15.0`, o que esta medido
e que a AWS passou a reafirmar o default do PySpark por release na serie 7.x --
nao que a 6.15.0 nao tivesse Python. Distinguir as duas coisas exige release
notes estruturadas, e e exatamente por isso que `deprecated` sai em
`unresolved` (ver abaixo). `added`/`removed` ficam, porque a presenca da celula
E fact medido; a leitura causal dela e que nao e.

Por isso tambem componente que UMA DAS DUAS plataformas nao publica como eixo
NUNCA vira `added` nem `removed`. Dizer "o EKS removeu o Hadoop" na comparacao
EC2 x EKS seria a mentira por omissao que o campo `unresolved` existe para nao
contar: o EKS nao removeu Hadoop, a fonte do EKS nao publica Hadoop (0 de 34
paginas). Esses caem em `unresolved`, com a chave `component.<nome>`.

AS SETE DIMENSOES DO §8.2, E AS CINCO QUE A MATRIZ NAO SUSTENTA (D-5).

Medido em 2026-08-31 contra `knowledge/`:

  added, removed          TEM LASTRO. A presenca da celula por release e o que
                          as quatro matrizes carregam.
  deprecated              SEM LASTRO.
  default_changes         SEM LASTRO -- e a que mais se parece com ter. A §2 de
                          `knowledge/glue/runtime-matrix.md` DISCUTE mudanca de
                          default ("AQE e default desde Spark 3.2", "ANSI mode
                          e default no Spark 4.1"), mas em PROSA e chaveada por
                          versao de SPARK, nao por release de plataforma, e so
                          para o Glue. As outras tres plataformas nao tem nem a
                          prosa. Emitir o que existe para uma das quatro e nada
                          para tres seria pior que recusar: o operador de EMR
                          leria lista vazia como "nenhum default mudou".
  compatibility_changes   SEM LASTRO pela mesma razao, com um agravante: o que
                          existe estruturado sobre compatibilidade e o CATALOGO
                          DE REGRAS (`rules/catalog/glue-migration.yaml`,
                          `SF-MIG-*`, com `runtime_scope` real). Consumir regra
                          aqui transformaria o diff de leitor em juiz, e a D-6
                          da spec e explicita: este sub-projeto entrega dado,
                          modelo e verbo, nenhuma regra.
  security_changes        SEM LASTRO.
  performance_changes     SEM LASTRO.

As cinco saem em `unresolved` COM A MEDIDA QUE AS DESTRAVARIA, nunca como lista
vazia -- que o operador leria como "nao mudou nada". Listar a recusa e a
diferenca entre "nao sei" e "nao perguntei".

DETERMINISMO. Toda colecao sai ordenada por nome de componente e toda chave de
`unresolved` e derivada da entrada; duas chamadas com os mesmos dois descritores
produzem `to_dict()` identico.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from sparkforge.migration.release_descriptor import (
    COMPONENT_UNIVERSE,
    PLATFORM_DOES_NOT_PUBLISH,
    ReleaseDescriptor,
)

# Ordem fixa dos eixos: da dimensao mais grossa para a mais fina. Fixa e nao
# ordenada alfabeticamente por acaso -- `platform` antes de `release` e a ordem
# em que o operador tem de ler, porque trocar de plataforma reenquadra o
# significado de trocar de release, e nao o contrario.
_ORDEM_DOS_EIXOS: tuple[str, ...] = ("platform", "release")

# As sete que o §8.2 do prompt mestre pede.
DIMENSOES_DO_82: tuple[str, ...] = (
    "added",
    "removed",
    "deprecated",
    "default_changes",
    "compatibility_changes",
    "security_changes",
    "performance_changes",
)

_SEM_LASTRO: Mapping[str, str] = MappingProxyType(
    {
        "compatibility_changes": (
            "exige uma tabela de compatibilidade por release, com o par (componente, "
            "versao) e a consequencia declarada; hoje o que existe estruturado sobre "
            "compatibilidade e o CATALOGO DE REGRAS (rules/catalog/glue-migration.yaml, "
            "SF-MIG-*, com runtime_scope real), e consumi-lo aqui transformaria este "
            "verbo de leitor em juiz -- a D-6 da spec proibe regra neste sub-projeto. "
            "Em knowledge/ ha prosa (secao 2 de knowledge/glue/runtime-matrix.md, "
            "knowledge/runtime-compatibility.md), so para o Glue e nao por release"
        ),
        "default_changes": (
            "exige as viradas de default declaradas por release e com fonte; hoje "
            "knowledge/glue/runtime-matrix.md as discute em PROSA e chaveadas por versao "
            "de Spark ('AQE e default desde Spark 3.2', 'ANSI mode e default no Spark "
            "4.1'), e knowledge/emr/, knowledge/emr-eks/ e knowledge/emr-serverless/ nao "
            "tem nem a prosa. Destrava com knowledge/<plataforma>/default-changes.yaml, "
            "chaveado por release, com propriedade, valor antes, valor depois e fonte"
        ),
        "deprecated": (
            "exige release notes estruturadas por release; hoje knowledge/emr/, "
            "knowledge/emr-eks/, knowledge/emr-serverless/ e knowledge/glue/ tem prosa e "
            "tabela de COMPONENTES, nao changelog. Destrava com "
            "knowledge/<plataforma>/release-notes.yaml carregando, por release, entradas "
            "`deprecated: [{api, desde, substituto, source, retrieved}]`. Sem isso este "
            "verbo nao distingue 'a plataforma parou de embarcar' de 'a fonte parou de "
            "publicar', que e a mesma ausencia de celula vista de dois lados"
        ),
        "performance_changes": (
            "exige baseline medido dos dois lados, nao documento: mudanca de desempenho "
            "entre releases e diferenca de tempo e de recurso no MESMO workload, e "
            "nenhuma matriz de knowledge/ carrega medida de execucao. Destrava com dois "
            "conjuntos de facts de event log e o verbo `benchmark`, que ja existe neste "
            "motor para exatamente essa pergunta -- nao com uma coluna nova de knowledge/"
        ),
        "security_changes": (
            "exige boletim de seguranca por release, com CVE e componente afetado; hoje "
            "nenhuma das quatro paginas de knowledge/<plataforma>/runtime-matrix.md cita "
            "CVE, e as matrizes carregam versao de componente e nada mais. Destrava com "
            "knowledge/<plataforma>/security-bulletins.yaml chaveado por release, com "
            "CVE, componente, severidade e fonte oficial em knowledge/sources.lock.json"
        ),
    }
)

# As cinco dimensoes do §8.2 que a matriz NAO sustenta, em ordem fixa.
DIMENSOES_SEM_LASTRO: tuple[str, ...] = tuple(sorted(_SEM_LASTRO))

# As duas que tem lastro. `DIMENSOES_DO_82` e a uniao das duas listas, e
# `tests/test_release_diff.py` trava essa particao -- dimensao do §8.2 que nao
# estivesse em nenhuma das duas sairia da saida sem ninguem notar.
DIMENSOES_COM_LASTRO: tuple[str, ...] = ("added", "removed")

_ATRIBUICAO_RECUSADA = (
    "as duas dimensoes variam ao mesmo tempo (platform E release), entao nenhuma linha "
    "de `changed` pode ser atribuida a uma delas isoladamente -- o valor de Iceberg pode "
    "ter mudado porque a release avancou, porque a plataforma e outra, ou pelos dois. "
    "Os numeros dos dois lados sao fact e estao emitidos; a ATRIBUICAO e que nao tem "
    "base. Destrava com dois diffs de um eixo cada: um fixando a plataforma e variando a "
    "release, outro fixando a release e variando a plataforma"
)


@dataclass(frozen=True)
class ComponentChange:
    """Um componente que os dois lados resolvem com valores diferentes.

    `from_value`/`to_value` e nao `from`/`to` porque `from` e palavra reservada
    do Python; `to_dict` emite as chaves `from` e `to` que a spec declara.
    """

    component: str
    from_value: str | tuple[str, ...]
    to_value: str | tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "from": list(self.from_value)
            if isinstance(self.from_value, tuple)
            else self.from_value,
            "to": list(self.to_value)
            if isinstance(self.to_value, tuple)
            else self.to_value,
        }


@dataclass(frozen=True)
class ReleaseDiff:
    """O que mudou entre dois descritores, e o que nao pode ser afirmado."""

    axis: tuple[str, ...]
    left: ReleaseDescriptor
    right: ReleaseDescriptor
    changed: tuple[ComponentChange, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged: tuple[str, ...]
    unresolved: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis": list(self.axis),
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "changed": [entrada.to_dict() for entrada in self.changed],
            "added": list(self.added),
            "removed": list(self.removed),
            "unchanged": list(self.unchanged),
            "unresolved": dict(sorted(self.unresolved.items())),
        }


def _eixos(left: ReleaseDescriptor, right: ReleaseDescriptor) -> tuple[str, ...]:
    variam = set()
    if left.platform != right.platform:
        variam.add("platform")
    if left.release != right.release:
        variam.add("release")
    return tuple(eixo for eixo in _ORDEM_DOS_EIXOS if eixo in variam)


def _onde(descritor: ReleaseDescriptor) -> str:
    return f"{descritor.platform}/{descritor.release}"


def _nao_comparavel(
    componente: str,
    left: ReleaseDescriptor,
    right: ReleaseDescriptor,
) -> str:
    razoes = [
        f"em {_onde(descritor)}: {descritor.refused[componente].reason}"
        for descritor in (left, right)
        if componente in descritor.refused
    ]
    return (
        f"`{componente}` nao e comparavel entre {_onde(left)} e {_onde(right)} -- "
        + "; ".join(razoes)
    )


def diff(left: ReleaseDescriptor, right: ReleaseDescriptor) -> ReleaseDiff:
    """Compara dois descritores e declara o eixo da comparacao.

    A ordem importa e e a do operador: `left` e de onde ele sai, `right` e para
    onde ele vai. `changed` le "de `from` para `to`" nessa direcao, e trocar os
    dois lados produz um diff diferente de proposito.
    """
    mudou: list[ComponentChange] = []
    acrescentados: list[str] = []
    removidos: list[str] = []
    iguais: list[str] = []
    recusados: dict[str, str] = {}

    for componente in COMPONENT_UNIVERSE:
        esquerda = left.components.get(componente)
        direita = right.components.get(componente)
        if esquerda is not None and direita is not None:
            if esquerda.version == direita.version:
                iguais.append(componente)
            else:
                mudou.append(
                    ComponentChange(
                        component=componente,
                        from_value=esquerda.version,
                        to_value=direita.version,
                    )
                )
            continue
        # Pelo menos um lado recusa. Se a recusa e "a fonte daquela plataforma
        # nao publica este eixo", a diferenca nao e do produto e nao pode virar
        # added/removed -- ver o docstring do modulo.
        ausente = left if esquerda is None else right
        outro_tambem_ausente = esquerda is None and direita is None
        eixo_inexistente = any(
            descritor.refused[componente].kind == PLATFORM_DOES_NOT_PUBLISH
            for descritor in (left, right)
            if componente in descritor.refused
        )
        if outro_tambem_ausente or eixo_inexistente:
            recusados[f"component.{componente}"] = _nao_comparavel(
                componente, left, right
            )
            continue
        if ausente is left:
            acrescentados.append(componente)
        else:
            removidos.append(componente)

    for dimensao in DIMENSOES_SEM_LASTRO:
        recusados[dimensao] = _SEM_LASTRO[dimensao]

    eixos = _eixos(left, right)
    if len(eixos) > 1:
        recusados["attribution"] = _ATRIBUICAO_RECUSADA

    return ReleaseDiff(
        axis=eixos,
        left=left,
        right=right,
        changed=tuple(sorted(mudou, key=lambda entrada: entrada.component)),
        added=tuple(sorted(acrescentados)),
        removed=tuple(sorted(removidos)),
        unchanged=tuple(sorted(iguais)),
        unresolved=MappingProxyType(dict(sorted(recusados.items()))),
    )
