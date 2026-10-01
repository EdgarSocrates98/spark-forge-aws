"""Migracao entre versoes de Control-M: qual capacidade muda, e em qual degrau.

## Por que este modulo existe separado de `migration/assessment.py`

As duas formas NAO sao a mesma, e achata-las seria o erro que a D-1 do
incremento 1 recusou por escrito.

`migration.release_descriptor.describe(platform, version)` devolve
`components: {nome: Component(version)}` -- mapa componente para versao. E o que
`_runtime_for` consome para montar o `runtime` de cada degrau de Glue e EMR, e o
julgamento acontece por `runtime_scope` de regra.

`controlm.descriptor.describe(version)` devolve outra coisa: **`capabilities`**,
cada uma com `boundary` em `introduced_in`, `changed_in`, `deprecated_from` ou
`discontinued_in`. A forma de Control-M e MAIS RICA para migracao -- ela ja
carrega a fronteira --, e for�a-la no molde de componente perderia exatamente o
campo que importa.

## Por que nao ha eixo `controlm` em `runtime_scope`

A D-f do incremento 2 decidiu isso e a razao nao mudou: `runtime_scope` guarda a
versao do `RuntimeContext` (Glue, Spark, Python, Iceberg), e nada ali conhece
`9.0.2x.yyy`. A versao de Control-M e DADO DO ARTEFATO, e viaja em
`declared_version` -- que ja e parametro de `extract_controlm_jobs`.

Entao o degrau aqui nao chama `judge` com um runtime: ele **reexecuta o
cruzamento que o extrator ja faz**, uma vez por versao do caminho, e compara os
vereditos. Nenhum mecanismo novo.

## As quatro fronteiras NAO valem o mesmo

Subindo de versao:

    introduced_in    a capacidade passa a existir -- GANHO, nao risco
    changed_in       continua la e se comporta diferente -- o mais traicoeiro
    deprecated_from  avisada, ainda funciona -- AVISO
    discontinued_in  sumiu -- QUEBRA

Um relatorio que as somasse num "N mudancas" esconderia a unica que derruba o
job. `SEVERIDADE_POR_FRONTEIRA` as separa, e `descer` inverte o sinal das duas
pontas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sparkforge.controlm import descriptor as cm_descriptor
from sparkforge.controlm import matrix as cm_matrix

# Como cada fronteira pesa numa migracao PARA FRENTE. Descendo, `_inverter` troca
# os dois extremos -- o que era ganho vira perda.
#
# `changed_in` e `break` e nao `warn` de proposito: a capacidade continua la, o
# job continua chamando, e o comportamento e outro. Um aviso convidaria a adiar
# a leitura da mudanca, que e o caso em que ela morde.
SEVERIDADE_POR_FRONTEIRA: dict[str, str] = {
    "introduced_in": "gain",
    "changed_in": "break",
    "deprecated_from": "warn",
    "discontinued_in": "break",
}

# O pior vence, e a ordem e esta. `unresolved` fica ACIMA de `ok` e abaixo de
# `warn`: nao saber e pior que saber que esta bem, e melhor que saber que quebra.
_ORDEM = ("ok", "gain", "unresolved", "warn", "break")

_GATE = {
    "break": "incompatible",
    "warn": "review_required",
    "unresolved": "unresolved",
    "gain": "compatible",
    "ok": "compatible",
}


class ControlMMigrationError(ValueError):
    """Erro de entrada da migracao de Control-M."""


@dataclass(frozen=True)
class MudancaDeCapacidade:
    """Uma capacidade que muda de estado entre duas versoes adjacentes."""

    capability: str
    de: str
    para: str
    boundary: str
    severity: str
    declared_at: str
    summary: str
    replaced_by: str | None = None


@dataclass(frozen=True)
class Degrau:
    """Um par adjacente de versoes, e o que muda nele."""

    de: str
    para: str
    direcao: str
    mudancas: tuple[MudancaDeCapacidade, ...] = ()

    @property
    def gate(self) -> str:
        pior = "ok"
        for m in self.mudancas:
            if _ORDEM.index(m.severity) > _ORDEM.index(pior):
                pior = m.severity
        return _GATE[pior]


@dataclass(frozen=True)
class AvaliacaoDeMigracao:
    """O relatorio, na MESMA forma que `MigrationAssessment` publica.

    A forma do relatorio e contrato com quem consome; so a fonte do veredito
    muda. Quem le `migration_assess` de Glue reconhece esta saida.
    """

    source: str
    target: str
    direcao: str
    degraus: tuple[Degrau, ...]
    capacidades_do_job: tuple[str, ...] = ()
    unresolved: tuple[dict[str, Any], ...] = field(default=())

    @property
    def gate(self) -> str:
        pior = "compatible"
        ordem = ("compatible", "unresolved", "review_required", "incompatible")
        for d in self.degraus:
            if ordem.index(d.gate) > ordem.index(pior):
                pior = d.gate
        return pior

    @property
    def quebras(self) -> tuple[MudancaDeCapacidade, ...]:
        return tuple(
            m for d in self.degraus for m in d.mudancas if m.severity == "break"
        )


def _ordenaveis() -> list[str]:
    """As versoes da matriz em ordem CRESCENTE de versao, nao editorial.

    `known_versions()` devolve na ordem em que o YAML as declara, que e a ordem
    da fonte (mais nova primeiro). Ordem editorial nao e ordem de caminho.
    """
    return sorted(
        cm_matrix.known_versions(),
        key=lambda v: tuple(int(p) for p in v.split(".")),
    )


def caminho(source: str, target: str) -> list[tuple[str, str]]:
    """Os degraus adjacentes de `source` ate `target`, nos DOIS sentidos.

    Diferente de `migration.version_path.steps`, que recusa alvo anterior a
    origem: descer de versao e caso legitimo em Control-M -- um cliente pode
    estar migrando um job para um ambiente mais antigo --, e e exatamente onde
    `introduced_in` morde. Recusar a descida esconderia a metade dos casos em
    que a fronteira importa.

    Origem igual a alvo devolve lista vazia: nao ha degrau, e isso e resposta.
    """
    conhecidas = _ordenaveis()
    for rotulo in (source, target):
        if rotulo not in conhecidas:
            raise ControlMMigrationError(
                f"versao {rotulo!r} fora da matriz de Control-M. A matriz cobre "
                f"{conhecidas[0]} a {conhecidas[-1]} e a fonte anda de 5 em 5 -- "
                f"`9.0.21.301` nao existe. Conhecidas: {', '.join(conhecidas)}"
            )
    i, j = conhecidas.index(source), conhecidas.index(target)
    if i == j:
        return []
    if i < j:
        return [(conhecidas[k], conhecidas[k + 1]) for k in range(i, j)]
    return [(conhecidas[k], conhecidas[k - 1]) for k in range(i, j, -1)]


def _capacidades(versao: str) -> dict[str, dict[str, Any]]:
    d = cm_descriptor.describe(versao)
    return dict(d.capabilities)


def _mudancas_do_degrau(de: str, para: str, alvo: set[str]) -> list[MudancaDeCapacidade]:
    """As capacidades de `alvo` cujo estado difere entre `de` e `para`.

    `alvo` e o conjunto que O JOB usa. Reportar toda capacidade da matriz faria o
    relatorio crescer com a fonte em vez de com o artefato -- e a pergunta que
    ele responde e "o que quebra NESTE job", nao "o que mudou na versao".

    ## Nao ha inversao por direcao, e a razao esta MEDIDA

    A primeira versao deste modulo tinha um `_inverter(severidade)` que trocava
    `gain` por `break` ao descer. Ele estava errado, e o teste de migracao para
    tras o pegou: descer de `9.0.22.005` para `9.0.21.300` com um job que usa
    `Job:DetachedEmbeddedScript` dava `gain` e gate `compatible`, quando a
    capacidade simplesmente NAO EXISTE no destino.

    A causa: `descriptor.describe(v)` e CUMULATIVO -- ele lista as capacidades
    disponiveis EM `v`. Medido: `9.0.22.000` tem 34 capacidades e nao inclui
    `job_detached_embedded_script`; `9.0.22.005` tem 35 e inclui. Entao a
    presenca no `de` e a ausencia no `para` **ja codificam a direcao**, e
    inverter depois disso era inverter duas vezes a mesma coisa.

    O veredito sai da comparacao dos dois conjuntos, e so dela:

        existe em `de`, some em `para`  -> break  (perda, em qualquer sentido)
        nao existe em `de`, surge       -> gain   (ganho, em qualquer sentido)
        existe nos dois e mudou         -> a fronteira decide
    """
    antes, depois = _capacidades(de), _capacidades(para)
    saida: list[MudancaDeCapacidade] = []

    for nome in sorted(alvo):
        a, b = antes.get(nome), depois.get(nome)
        if a == b:
            continue
        # A fronteira que descreve a MUDANCA e a do lado onde a capacidade foi
        # declarada -- `depois` quando ela aparece ou muda, `antes` quando ela
        # some. Sem essa escolha, uma capacidade removida sairia sem fronteira.
        fonte = b if b is not None else a
        if fonte is None:
            continue
        boundary = str(fonte.get("boundary") or "changed_in")
        if b is None:
            # Sumiu no destino: perda, qualquer que seja a fronteira que a
            # declarou e qualquer que seja o sentido da viagem.
            severidade = "break"
        elif a is None:
            # Surgiu no destino: ganho, pela mesma simetria.
            severidade = "gain"
        else:
            # Nos dois lados e diferente: a fronteira e quem sabe o que mudou.
            severidade = SEVERIDADE_POR_FRONTEIRA.get(boundary, "unresolved")
        saida.append(
            MudancaDeCapacidade(
                capability=nome,
                de=de,
                para=para,
                boundary=boundary,
                severity=severidade,
                declared_at=str(fonte.get("declared_at") or ""),
                summary=str(fonte.get("summary") or ""),
                replaced_by=fonte.get("replaced_by"),
            )
        )
    return saida


def _capacidades_do_job(facts: list[Any]) -> tuple[set[str], list[dict[str, Any]]]:
    """As capacidades que o job usa, e as recusas que o extrator nomeou.

    Le os kinds que o incremento 2 ja emite. Nao reinterpreta artefato: se o
    extrator nao viu a capacidade, ela nao entra -- e a recusa dele viaja junto
    em vez de virar ausencia.
    """
    usadas: set[str] = set()
    recusas: list[dict[str, Any]] = []
    for f in facts:
        kind = getattr(f, "kind", "")
        attrs = dict(getattr(f, "attrs", {}) or {})
        nome = str(attrs.get("capability") or "")
        if kind in ("ctm.capability_supported", "ctm.capability_incompatible") and nome:
            usadas.add(nome)
        elif kind == "ctm.capability_unresolved":
            recusas.append(
                {
                    "capability": nome,
                    "reason": attrs.get("reason"),
                    "unblocked_by": attrs.get("unblocked_by"),
                }
            )
    return usadas, recusas


def avaliar(facts: list[Any], source: str, target: str) -> AvaliacaoDeMigracao:
    """Avalia a migracao de um job de `source` para `target`.

    `facts` sao os do extrator de `Jobs-as-Code`, extraidos UMA vez -- com
    qualquer `declared_version`, porque o que se le deles e o conjunto de
    capacidades que o job usa, e esse conjunto nao depende da versao declarada.
    O cruzamento por versao acontece aqui, degrau a degrau.
    """
    degraus_brutos = caminho(source, target)
    usadas, recusas = _capacidades_do_job(facts)
    subindo = tuple(int(p) for p in source.split(".")) <= tuple(
        int(p) for p in target.split(".")
    )
    direcao = "forward" if subindo else "backward"

    degraus = tuple(
        Degrau(
            de=de,
            para=para,
            direcao=direcao,
            mudancas=tuple(_mudancas_do_degrau(de, para, usadas)),
        )
        for de, para in degraus_brutos
    )
    return AvaliacaoDeMigracao(
        source=source,
        target=target,
        direcao=direcao,
        degraus=degraus,
        capacidades_do_job=tuple(sorted(usadas)),
        unresolved=tuple(recusas),
    )


__all__ = [
    "SEVERIDADE_POR_FRONTEIRA",
    "AvaliacaoDeMigracao",
    "ControlMMigrationError",
    "Degrau",
    "MudancaDeCapacidade",
    "avaliar",
    "caminho",
]
