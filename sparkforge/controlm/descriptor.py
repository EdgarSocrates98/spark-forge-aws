"""`describe` do Control-M Automation API -- o que vale numa versao, com a recusa NOMEADA.

A PERGUNTA QUE ESTE MODULO RESPONDE, e ela e a que o operador trouxe: *"estou na
`9.0.21.300` -- o que posso usar?"*. Nao e *"o que quebra de X para Y"*. O
operador atua em clientes com versoes diferentes e precisa saber, por versao,
quais capacidades existem e quais exigencias de componente valem.

A COMPOSICAO E LEITURA DE FRONTEIRA, NAO INTERPOLACAO -- e a distincao importa
porque a §12 do `CLAUDE.md` proibe interpolar entre observacoes. Uma capacidade
com `introduced_in: 9.0.21.300` existe em toda versao >= `9.0.21.300` da faixa
porque e isso que a frase da fonte AFIRMA ("is now available in"), nao porque se
esteja adivinhando o meio do caminho. Para nao deixar isso implicito, cada item
da saida carrega `declared_at` -- a versao onde a fronteira foi lida --, entao a
resposta sobre Java em `9.0.22.060` diz, na propria linha, que vem de
`9.0.21.325`.

AS DUAS RECUSAS, com nomes diferentes porque destravam com medidas diferentes --
o mesmo desenho de `sparkforge/migration/release_descriptor.py`:

  `VERSION_OUTSIDE_RANGE`   a versao esta fora de `covers`. `9.0.22.125` existe
                            na pagina e esta ACIMA do teto; `9.0.21.130` esta
                            abaixo do piso. Destrava com uma DECISAO de ampliar
                            a faixa mais a leitura das versoes novas -- nunca
                            extrapolando da fronteira mais proxima.
  `VERSION_NOT_PUBLISHED`   a versao esta DENTRO da faixa e a fonte nao a
                            publica. `9.0.21.301` nao existe: a fonte anda de 5
                            em 5. Destrava com uma leitura que mostre que ela
                            existe -- e nao respondendo pelo degrau de baixo,
                            que seria interpolar entre duas versoes observadas.

O QUE ESTE MODULO NAO FAZ, e a razao esta na D-4 da spec: ele nao julga. Nenhum
`Finding` nasce aqui e nenhuma linha da saida diz se algo quebra. Nao ha
artefato do operador para extrair e nao ha corpus para sustentar regra; regra
sobre definicao de job depende do extrator de `Jobs-as-Code`, que e o incremento
2. Este verbo entrega DADO e CONSULTA.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from sparkforge.controlm import matrix as cm

VERSION_OUTSIDE_RANGE = "version_outside_covered_range"
VERSION_NOT_PUBLISHED = "version_not_published_by_source"

# As fronteiras que dizem "existe a partir de", contra as que dizem "deixa de
# existir a partir de". Separadas porque a resposta de `describe` e diferente:
# a primeira familia entra em `capabilities` e a segunda em `deprecated`, e
# colapsa-las faria o operador ler `config em:param::set` como disponivel.
_DISPONIBILIZA: tuple[str, ...] = ("introduced_in", "changed_in")
_RETIRA: tuple[str, ...] = ("deprecated_from", "discontinued_in")


class ControlMDescriptorError(ValueError):
    """Base das recusas deste modulo, para quem quiser capturar as duas."""


class UnknownVersion(ControlMDescriptorError):
    """Versao que esta matriz nao sustenta -- fora da faixa ou nao publicada.

    Erro NOMEADO e nao `KeyError` porque as duas fronteiras sao diferentes e um
    `KeyError` nao diz qual delas foi cruzada. `kind` carrega o nome, e a
    mensagem carrega o intervalo que a matriz sustenta.
    """

    def __init__(self, message: str, kind: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class VersionDescriptor:
    """O que vale numa versao do Automation API, segundo esta fonte e so ela.

    `declared_here` e o que esta versao DECLARA, de qualquer das quatro
    fronteiras -- e o campo se chamou `introduced_here` ate a primeira leitura da
    saida real, que mostrou o nome mentindo: `9.0.21.300` declara seis
    capacidades novas E retira duas (`config em:param::set` depreciado,
    `config server:params::get` descontinuado), e as oito saiam sob um nome que
    prometia so as seis.
    """

    version: str
    covers: tuple[str, str]
    capabilities: Mapping[str, dict[str, Any]]
    deprecated: Mapping[str, dict[str, Any]]
    components: Mapping[str, dict[str, Any]]
    declared_here: tuple[str, ...]
    unresolved: tuple[str, ...]
    unresolved_detail: Mapping[str, dict[str, Any]]
    sources: tuple[str, ...]
    retrieved: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": "controlm_automation_api",
            "version": self.version,
            "covers": {"from": self.covers[0], "to": self.covers[1]},
            "capabilities": {k: dict(v) for k, v in sorted(self.capabilities.items())},
            "deprecated": {k: dict(v) for k, v in sorted(self.deprecated.items())},
            "components": {k: dict(v) for k, v in sorted(self.components.items())},
            "declared_here": list(self.declared_here),
            "unresolved": list(self.unresolved),
            "unresolved_detail": {
                k: dict(self.unresolved_detail[k]) for k in self.unresolved
            },
            "sources": list(self.sources),
            "retrieved": self.retrieved,
        }


def _recusa_fora_da_faixa(versao: str, piso: str, teto: str) -> UnknownVersion:
    return UnknownVersion(
        f"versao {versao!r} fora da faixa que esta matriz sustenta: "
        f"{piso} a {teto}. A faixa e passado FECHADO e nao se extrapola -- "
        f"a fonte publica versoes fora dela (ate 9.0.22.125 em 2026-09-01), e "
        f"traze-las exige LER a pagina daquelas versoes e ampliar `covers` em "
        f"knowledge/controlm/automation-api-matrix.yaml, nunca derivar da "
        f"fronteira mais proxima",
        VERSION_OUTSIDE_RANGE,
    )


def _recusa_nao_publicada(versao: str, conhecidas: tuple[str, ...]) -> UnknownVersion:
    return UnknownVersion(
        f"versao {versao!r} esta dentro da faixa e a fonte nao a publica. "
        f"A fonte anda de 5 em 5, e responder pelo degrau de baixo seria "
        f"interpolar entre duas versoes observadas. "
        f"conhecidas: {', '.join(conhecidas)}",
        VERSION_NOT_PUBLISHED,
    )


def known_versions() -> tuple[str, ...]:
    """As versoes que esta matriz sustenta, em ordem crescente."""
    return cm.known_versions()


def describe(version: str) -> VersionDescriptor:
    """O descritor de uma versao do Automation API.

    Versao fora da faixa coberta, ou dentro dela mas nao publicada pela fonte,
    levanta `UnknownVersion` com o `kind` que diz qual das duas fronteiras foi
    cruzada e com o intervalo que a matriz sustenta. Nunca `KeyError`, nunca
    `UNKNOWN` mudo, e nunca a resposta da versao vizinha.
    """
    alvo = str(version).strip()
    piso, teto = cm.covers()
    chave = cm.version_key(alvo)
    if not (cm.version_key(piso) <= chave <= cm.version_key(teto)):
        raise _recusa_fora_da_faixa(alvo, piso, teto)
    conhecidas = cm.known_versions()
    if alvo not in conhecidas:
        raise _recusa_nao_publicada(alvo, conhecidas)

    documento = cm.load()
    fontes = cm.sources()
    lido_em = cm.retrieved()

    capacidades: dict[str, dict[str, Any]] = {}
    retiradas: dict[str, dict[str, Any]] = {}
    aqui: list[str] = []
    for slug, entrada in documento["capabilities"].items():
        fronteira = next(b for b in cm.BOUNDARIES if entrada.get(b))
        declarada = str(entrada[fronteira])
        if cm.version_key(declarada) > chave:
            continue
        linha = {
            "summary": str(entrada["summary"]),
            "boundary": fronteira,
            "declared_at": declarada,
            "replaced_by": str(entrada["replaced_by"]) if entrada.get("replaced_by") else None,
        }
        destino = capacidades if fronteira in _DISPONIBILIZA else retiradas
        destino[str(slug)] = linha
        if declarada == alvo:
            aqui.append(str(slug))

    componentes: dict[str, dict[str, Any]] = {}
    for nome, versoes in documento["components"].items():
        # A celula que VALE e a mais recente cujo declarado <= alvo. Hoje cada
        # componente tem uma celula so na faixa, e a conta esta escrita assim
        # mesmo assim: a segunda celula de `java` entra no dia em que a BMC
        # exigir Java 21, e um `next(iter(...))` escolheria a errada em silencio.
        candidatas = [v for v in versoes if cm.version_key(str(v)) <= chave]
        if not candidatas:
            continue
        vigente = max(candidatas, key=lambda v: cm.version_key(str(v)))
        celula = dict(versoes[vigente])
        celula["declared_at"] = str(vigente)
        componentes[str(nome)] = celula

    recusas = {
        str(k): {"item": str(k), "reason": str(v["reason"])}
        for k, v in documento["unresolved"].items()
    }
    # A recusa da PROPRIA versao vem primeiro na leitura de quem pergunta por
    # ela, mas a lista sai ordenada -- a saida e determinista e o consumidor
    # acha `9.0.22.100` pelo nome, nao pela posicao.
    return VersionDescriptor(
        version=alvo,
        covers=(piso, teto),
        capabilities=MappingProxyType(capacidades),
        deprecated=MappingProxyType(retiradas),
        components=MappingProxyType(componentes),
        declared_here=tuple(sorted(aqui)),
        unresolved=tuple(sorted(recusas)),
        unresolved_detail=MappingProxyType(recusas),
        sources=fontes,
        retrieved=lido_em,
    )


def describe_all() -> tuple[VersionDescriptor, ...]:
    """Os descritores das 31 versoes da faixa. O que os testes de invariante
    rodam sobre a faixa inteira em vez de sobre amostra."""
    return tuple(describe(v) for v in known_versions())
