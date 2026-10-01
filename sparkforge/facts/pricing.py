"""Carrega o preco publicado do AWS Glue como dado com data e regiao.

POR QUE ESTE MODULO NAO CALCULA NADA. A secao 51 pede conhecimento de preco com
data e regiao, e proibe explicitamente codificar a reducao anunciada como
constante. As duas fontes oficiais lidas em 2026-08-23 nao dizem a mesma coisa:
a pagina de pricing publica UM preco por DPU-hora e nao diferencia por versao de
runtime; o anuncio do Glue 6.0 afirma uma reducao percentual sem nomear a versao
de comparacao, sem regiao e sem tipo de worker. Multiplicar um pelo outro
produziria um preco por versao que fonte nenhuma publica -- por isso `prices` e
`announcements` sao listas SEPARADAS, e nao ha funcao que combine as duas.

O carregador e fail-closed pelo mesmo motivo de
`sparkforge/facts/runtime_matrix.py` e `sparkforge/storage/feature_support.py`:
uma entrada de preco sem `source`, `source_type` e `retrieved` carregaria em
silencio e viraria, tres saltos adiante, um numero de custo num relatorio. Numero
de custo envelhecido nao parece errado -- parece preciso.

`UNQUALIFIED` e valor de primeira classe, nao ausencia. A pagina publica um
numero e a frase de que o preco varia por regiao, sem a tabela por regiao no
documento servido. Escrever `us-east-1` porque e o default comum seria precisao
fabricada, e precisao fabricada sobrevive a revisao melhor que ausencia
declarada.

RESOLUCAO DE CAMINHO: usa `sparkforge.knowledge_ref`, nunca a propria conta de
`parents[N]` -- `pyproject.toml` empacota `knowledge/` DENTRO do pacote
instalado, um nivel mais fundo do que a conta que funciona no checkout, e
reimplementar a resolucao aqui reproduziria aquele bug num modulo novo.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from sparkforge.facts.runtime_matrix import SOURCE_TYPES
from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file


class PricingError(ValueError):
    """Tabela de preco ausente, vazia ou com entrada sem evidencia."""


# Valor para o eixo que a FONTE nao qualifica. Distinto de campo ausente: este
# diz "a fonte foi lida e nao qualificou"; ausente diria "ninguem leu".
UNQUALIFIED = "UNQUALIFIED"

_CAMPOS_DE_EVIDENCIA = ("source", "source_type", "retrieved")

# Campos que toda entrada de preco precisa declarar alem da evidencia. `region`
# e `runtime_version` entram aqui, e nao como opcionais, porque preco sem eixo
# declarado e o defeito que esta tabela existe para impedir -- ate quando a
# resposta e `UNQUALIFIED`, ela precisa estar escrita.
_CAMPOS_DE_PRECO = ("value", "currency", "region", "runtime_version")

_CAMPOS_DE_ANUNCIO = ("claim", "runtime_version", "region", "worker_type")


def _validar(rotulo: str, entrada: dict[str, Any], obrigatorios: tuple[str, ...]) -> None:
    if not isinstance(entrada, dict):
        raise PricingError(f"{rotulo}: entrada precisa ser um mapa, veio {type(entrada).__name__}")
    for campo in obrigatorios:
        if campo not in entrada or entrada[campo] in (None, ""):
            raise PricingError(f"{rotulo}: campo obrigatorio ausente ou vazio: {campo}")
    for campo in _CAMPOS_DE_EVIDENCIA:
        if not entrada.get(campo):
            raise PricingError(
                f"{rotulo}: sem {campo}. Preco sem procedencia carrega em silencio e "
                f"vira numero de custo num relatorio"
            )
    if entrada["source_type"] not in SOURCE_TYPES:
        raise PricingError(
            f"{rotulo}: source_type {entrada['source_type']!r} fora de {sorted(SOURCE_TYPES)}"
        )


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """A tabela validada. Cache porque o arquivo nao muda na vida do processo."""
    caminho = safe_knowledge_file(knowledge_dir(), "glue/pricing.yaml")
    with caminho.open("r", encoding="utf-8") as arquivo:
        conteudo = yaml.safe_load(arquivo) or {}

    precos = conteudo.get("prices")
    if not precos:
        raise PricingError(
            f"{caminho}: bloco 'prices' ausente ou vazio -- uma tabela vazia nao "
            f"e a mesma coisa que um preco que ninguem publicou"
        )
    for indice, entrada in enumerate(precos):
        _validar(f"prices[{indice}]", entrada, _CAMPOS_DE_PRECO)

    # `announcements` PODE ser vazio: um periodo sem anuncio e estado normal.
    for indice, entrada in enumerate(conteudo.get("announcements") or []):
        _validar(f"announcements[{indice}]", entrada, _CAMPOS_DE_ANUNCIO)

    return {
        "unit": conteudo.get("unit", ""),
        "prices": list(precos),
        "announcements": list(conteudo.get("announcements") or []),
        # Vazio nao e "nao existe": e "a fonte lida nao os enumera".
        "worker_types": list(conteudo.get("worker_types") or []),
    }


def prices(runtime_version: str | None = None) -> list[dict[str, Any]]:
    """Os precos publicados, opcionalmente os de uma versao de runtime.

    Filtrar por versao devolve tambem as entradas `UNQUALIFIED`, e de proposito:
    a fonte publica um preco que vale para o servico sem recorte de versao, e
    esconde-lo de quem pergunta por `6.0` responderia "nao ha preco" quando ha.
    """
    todos = load()["prices"]
    if runtime_version is None:
        return list(todos)
    return [
        p
        for p in todos
        if p["runtime_version"] in (runtime_version, UNQUALIFIED)
    ]


def announcements(runtime_version: str | None = None) -> list[dict[str, Any]]:
    """Os anuncios de preco, COMO anuncios -- nunca convertidos em preco.

    Um anuncio sem `baseline` nao permite calcular o preco anterior: a fonte diz
    de quanto foi a reducao, nao de que numero ela partiu.
    """
    todos = load()["announcements"]
    if runtime_version is None:
        return list(todos)
    return [a for a in todos if a["runtime_version"] == runtime_version]


def differentiates_by_runtime_version() -> bool:
    """Alguma fonte publica preco POR versao de runtime?

    A resposta hoje e `False`, e ela e o resultado -- nao uma lacuna a preencher
    por inferencia. Quem quiser custo por versao precisa de uma fonte que o
    publique, e o relatorio deve dizer isso em vez de multiplicar o preco unico
    pela reducao anunciada.
    """
    return any(p["runtime_version"] != UNQUALIFIED for p in load()["prices"])
