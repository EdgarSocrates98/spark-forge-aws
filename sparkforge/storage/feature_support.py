"""Matriz de compatibilidade: feature de Iceberg CONTRA engine, como dado.

`knowledge/storage/iceberg-v3.md` ja separava em PROSA a metade "feature da
spec" da metade "suporte da engine", e ja dizia que uma nao se deduz da outra.
Prosa nao e consultavel e nao tem gate: nada impedia uma recomendacao de
atravessar da metade 1 para a metade 2 sem uma linha da metade 2 que a
sustentasse. Este modulo carrega `knowledge/storage/iceberg-feature-support.yaml`
e enforca, em codigo, a unica regra que torna a matriz confiavel:

    TODA CELULA AFIRMATIVA PRECISA DE EVIDENCIA PROPRIA. Nunca se infere "o
    Iceberg suporta, logo o Athena suporta".

E o mesmo mecanismo de `sparkforge/facts/runtime_matrix.py` aplicado a outro
eixo -- la o eixo e versao de runtime, aqui e feature contra engine -- com o
mesmo vocabulario de `source_type` (importado de la, nunca redeclarado) e a
mesma postura fail-closed: sem fonte, o carregador estoura na carga, e nao
devolve um status que ninguem consegue sustentar.

RESOLUCAO DE CAMINHO: este modulo usa `sparkforge.knowledge_ref`, e nao a sua
propria conta de `parents[N]`. A docstring de `sparkforge/facts/runtime_matrix.py`
registra o bug historico por extenso: `pyproject.toml` empacota `knowledge/`
DENTRO do pacote instalado (`"knowledge" = "sparkforge/knowledge"`), um nivel
mais fundo do que a conta que funciona no checkout de desenvolvimento, e o
resultado foi `FileNotFoundError` num wheel instalado. Reimplementar a
resolucao aqui seria reproduzir aquele bug num modulo novo.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.facts.runtime_matrix import SOURCE_TYPES
from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file


class FeatureSupportError(ValueError):
    """Matriz de features ausente, vazia ou com celula mal declarada.

    Estourar na carga e deliberado. Uma celula afirmativa sem fonte carregaria
    em silencio e viraria, tres saltos adiante, uma frase de relatorio com cara
    de fato -- que e exatamente o defeito que esta matriz existe para impedir.
    """


# Vocabulario FECHADO de `status`, o da secao 20 do prompt. Fechado pelo mesmo
# motivo que `SOURCE_TYPES` e fechado: status livre vira etiqueta decorativa em
# duas semanas, e o ponto de classificar suporte e poder dizer POR QUE uma
# celula nao e simplesmente "sim" ou "nao".
#   SUPPORTED    a engine executa a feature, e a fonte diz isso.
#   UNSUPPORTED  a engine NAO executa, e a fonte diz isso.
#   PARTIAL      executa dentro de um recorte que a `note` precisa nomear.
#   READ_ONLY    le o que outro escreveu, nao escreve.
#   WRITE_ONLY   escreve, nao le.
#   PREVIEW      disponivel sem garantia de estabilidade.
#   UNKNOWN      nao ha fonte. O unico status que dispensa evidencia.
#   CONFLICTING  duas fontes afirmam coisas incompativeis, e nenhuma vence.
SUPPORT_STATUS = frozenset(
    {
        "SUPPORTED",
        "UNSUPPORTED",
        "PARTIAL",
        "READ_ONLY",
        "WRITE_ONLY",
        "PREVIEW",
        "UNKNOWN",
        "CONFLICTING",
    }
)

# Versoes de spec que esta matriz sabe classificar. `v1` fica de fora porque
# nenhuma feature aqui e dela, e aceitar um numero que nenhuma linha usa seria
# vocabulario sem consumidor.
SPEC_VERSIONS = frozenset({2, 3})

# Chave de versao para afirmacao que a fonte NAO qualifica por versao da engine.
# Inventar "3.0" numa celula de Athena, so para a linha ficar simetrica com a do
# Glue, seria precisao fabricada -- e precisao fabricada sobrevive a revisao
# melhor do que ausencia declarada.
ANY_VERSION = "*"

# O unico status que dispensa fonte, e por que: desconhecimento nao precisa de
# prova, afirmacao precisa. Exigir fonte de `UNKNOWN` empurraria quem edita a
# inventar uma URL qualquer -- ou, pior, a APAGAR a celula, e celula apagada
# mente dizendo que a pergunta nunca foi feita.
_DISPENSA_FONTE = "UNKNOWN"

_CAMPOS_DE_EVIDENCIA = ("source", "source_type", "retrieved")


def _matrix_path() -> Path:
    return safe_knowledge_file(knowledge_dir(), "storage/iceberg-feature-support.yaml")


def _normalizar(celula: Any) -> dict[str, Any]:
    """Aceita a forma curta (`"6.0": UNKNOWN`) e devolve sempre a forma longa.

    A forma curta existe para que as dezenas de celulas desconhecidas caibam
    numa linha cada, em vez de tres. Ela nao e uma porta dos fundos: o valor
    normalizado passa pela MESMA validacao, entao `"6.0": SUPPORTED` sem fonte
    estoura igual.
    """
    if isinstance(celula, str):
        return {"status": celula}
    if isinstance(celula, dict):
        return celula
    raise FeatureSupportError(f"celula com forma inesperada: {celula!r}")


def _validar_celula(coordenada: str, celula: dict[str, Any]) -> None:
    status = celula.get("status")

    # DEFEITO IMPEDIDO: status inventado na hora da edicao ("MOSTLY", "YES",
    # "sim") que nenhum consumidor sabe interpretar e que passa despercebido
    # porque YAML aceita qualquer string.
    if status not in SUPPORT_STATUS:
        raise FeatureSupportError(
            f"{coordenada}: status {status!r} fora de {sorted(SUPPORT_STATUS)}"
        )

    if status == _DISPENSA_FONTE:
        return

    # DEFEITO IMPEDIDO: afirmar suporte (ou nao-suporte) sem nada que sustente
    # a afirmacao -- opiniao com cara de fato. E a forma pratica de violar a
    # regra da secao 20: ninguem escreve "eu acho"; escreve-se `SUPPORTED` numa
    # celula porque "o Iceberg suporta", e a inferencia proibida entra pela
    # ausencia de fonte, nunca por uma fonte errada.
    for campo in _CAMPOS_DE_EVIDENCIA:
        if not celula.get(campo):
            raise FeatureSupportError(
                f"{coordenada}: status {status} sem `{campo}` -- so UNKNOWN "
                "dispensa evidencia, porque desconhecimento nao precisa de prova"
            )

    # DEFEITO IMPEDIDO: fonte classificada com um rotulo que a matriz de runtime
    # nao conhece, o que quebraria a comparacao de qualidade entre fontes na hora
    # de resolver uma discordancia.
    if celula["source_type"] not in SOURCE_TYPES:
        raise FeatureSupportError(
            f"{coordenada}: source_type {celula['source_type']!r} fora de "
            f"{sorted(SOURCE_TYPES)}"
        )


@lru_cache(maxsize=1)
def load() -> dict[str, dict[str, Any]]:
    """As features validadas, indexadas pelo nome da feature.

    Cada feature devolve `{"spec_version": int | None, "engines": {engine:
    {versao: celula}}}`, com toda celula ja na forma longa. Cache com
    `lru_cache` porque o arquivo nao muda durante a vida do processo.
    """
    caminho = _matrix_path()
    with caminho.open("r", encoding="utf-8") as arquivo:
        conteudo = yaml.safe_load(arquivo)

    features = (conteudo or {}).get("features")
    if not features:
        raise FeatureSupportError(
            f"{caminho}: bloco 'features' ausente ou vazio -- uma matriz vazia "
            "responderia UNKNOWN a tudo, que e indistinguivel de nao saber nada"
        )

    resolvida: dict[str, dict[str, Any]] = {}
    for feature, dados in features.items():
        spec_version = dados.get("spec_version")
        # DEFEITO IMPEDIDO: feature carimbada com uma versao de spec que nao
        # existe neste vocabulario (typo "1", ou "4" antecipando formato que
        # ainda nao saiu). O campo alimenta a consequencia declarada em
        # `engines.athena.note`, entao um numero errado aqui propaga para a
        # leitura de uma celula inteira.
        if spec_version is not None and spec_version not in SPEC_VERSIONS:
            raise FeatureSupportError(
                f"{feature}: spec_version {spec_version!r} fora de {sorted(SPEC_VERSIONS)}"
            )

        engines: dict[str, dict[str, dict[str, Any]]] = {}
        for engine, versoes in (dados.get("engines") or {}).items():
            engines[engine] = {}
            for versao, celula in (versoes or {}).items():
                normalizada = _normalizar(celula)
                _validar_celula(f"{feature}.{engine}.{versao}", normalizada)
                engines[engine][str(versao)] = normalizada

        resolvida[feature] = {"spec_version": spec_version, "engines": engines}
    return resolvida


def cell(feature: str, engine: str, version: str = ANY_VERSION) -> dict[str, Any]:
    """A celula inteira, com evidencia. Celula ausente vira `UNKNOWN` sintetico.

    Ausencia NAO e excecao aqui. `KeyError` vazando deste modulo viraria
    `try/except KeyError` no chamador, e esse `except` engole tambem o erro de
    digitacao no nome da feature -- transformando um defeito em silencio.
    """
    versoes = load().get(feature, {}).get("engines", {}).get(engine, {})
    if version in versoes:
        return versoes[version]
    # A fonte pode nao qualificar por versao (ver `ANY_VERSION`). Quem pergunta
    # por uma versao concreta ainda deve receber a afirmacao nao-qualificada.
    if ANY_VERSION in versoes:
        return versoes[ANY_VERSION]
    return {"status": "UNKNOWN"}


def support(feature: str, engine: str, version: str = ANY_VERSION) -> str:
    """O status de uma celula. `UNKNOWN` quando a celula nao existe."""
    return cell(feature, engine, version)["status"]


def cells() -> list[tuple[str, str, str, dict[str, Any]]]:
    """Toda celula da matriz como `(feature, engine, versao, celula)`.

    Existe para que um gate consiga varrer a matriz inteira sem reimplementar a
    caminhada de tres niveis -- e a caminhada reimplementada em cada teste e
    como uma celula nova escapa de um gate antigo.
    """
    return [
        (feature, engine, versao, celula)
        for feature, dados in sorted(load().items())
        for engine, versoes in sorted(dados["engines"].items())
        for versao, celula in sorted(versoes.items())
    ]


def unknown_cells() -> list[tuple[str, str, str]]:
    """As celulas `UNKNOWN`, como `(feature, engine, versao)`.

    E o que um relatorio honesto MOSTRA em vez de omitir: a diferenca entre
    "esta engine nao suporta" e "ninguem tem fonte sobre esta engine" e a
    diferenca entre um plano de migracao e um chute com formatacao boa.
    """
    return [(f, e, v) for f, e, v, celula in cells() if celula["status"] == "UNKNOWN"]


def status_counts() -> dict[str, int]:
    """Quantas celulas em cada status. A forma curta do mesmo relatorio."""
    contagem: dict[str, int] = {}
    for _, _, _, celula in cells():
        contagem[celula["status"]] = contagem.get(celula["status"], 0) + 1
    return dict(sorted(contagem.items()))
