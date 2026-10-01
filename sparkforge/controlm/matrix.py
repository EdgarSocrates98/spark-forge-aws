"""Carrega a matriz do Control-M Automation API como dado, com vocabulario FECHADO.

O QUE ESTA MATRIZ E, E O QUE ELA NAO E. Ela e do **Automation API**, nao do
produto Control-M inteiro. As duas coisas carregam a mesma grafia de versao
(`9.0.2x.yyy`) e nao sao a mesma coisa: medido em 2026-09-01, do lado do
produto so `9.0.21.300` e `9.0.22` abrem raiz de documentacao propria. Celula
sobre o produto sai em `unresolved` com a razao, nunca preenchida por analogia.

DOIS EIXOS, E O CARREGADOR ENFORCA OS DOIS SEPARADAMENTE. A fonte tem dois
tipos de afirmacao, e cada uma vai para o eixo que a descreve:

  capabilities  capacidade com FRONTEIRA de versao (`Job:DetachedEmbeddedScript`
                existe a partir de `9.0.22.005`). Molde: a matriz de feature do
                Iceberg (`min_library_version`).
  components    componente com EXIGENCIA por versao (Java 11 deixa de ser
                suportado em `9.0.21.325`). Molde: as quatro matrizes de runtime.

`Java 11` NAO e componente com versao -- e fronteira de exigencia --, e forcar
os dois num eixo so faria celula que responde por coisas de naturezas
diferentes, que e pior que celula ausente porque ausencia e recusa e a celula e
afirmacao.

VOCABULARIO FECHADO, pela mesma razao de `_carrega_matriz_fechada` nas tres
matrizes de EMR: a unica forma pratica de esta matriz voltar a inventar eixo e
alguem acrescentar uma chave nova numa entrada porque "faz sentido". Chave fora
do conjunto estoura na CARGA, nomeando a chave e a entrada. Sao quatro conjuntos
fechados -- o do documento, o de uma capacidade, o de uma celula de componente e
o das fronteiras -- e nenhum deles e derivado do outro.

RESOLUCAO DE CAMINHO: `sparkforge.knowledge_ref`, e nao conta de `parents[N]`.
Pela mesma razao que `sparkforge/facts/runtime_matrix.py` documenta -- o
`pyproject.toml` empacota `knowledge/` DENTRO do pacote instalado, e uma conta
de profundidade escrita a mao quebra no wheel e passa no checkout.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file

_RELATIVE = "controlm/automation-api-matrix.yaml"


class ControlMMatrixError(ValueError):
    """Matriz ausente, vazia, ou com chave fora do vocabulario fechado.

    Erro proprio e nao `RuntimeMatrixError` porque as duas guardam contratos
    DIFERENTES: aquele guarda `versions:` com celula escalar por release, e este
    guarda dois eixos que nao tem `versions:` nenhum. Capturar os dois juntos
    esconderia qual dos dois contratos foi violado.
    """


# As chaves do documento. `covers` e obrigatoria e nao decorativa: e dela que
# `describe` tira o intervalo que ele SUSTENTA, e sem ela a recusa por fronteira
# nao teria o que nomear.
_DOCUMENTO = frozenset(
    {"schema_version", "retrieved", "covers", "sources", "capabilities", "components", "unresolved"}
)
_DOCUMENTO_OBRIGATORIAS = ("covers", "sources", "capabilities", "components", "unresolved")

# As quatro fronteiras que a fonte publica. Nao ha quinta, e uma capacidade sem
# nenhuma delas seria afirmacao sem versao -- exatamente o que esta matriz
# existe para nao produzir.
BOUNDARIES: tuple[str, ...] = (
    "introduced_in",
    "changed_in",
    "deprecated_from",
    "discontinued_in",
)

_CAPACIDADE = frozenset({"summary", "replaced_by", *BOUNDARIES})

# As chaves de uma celula de componente. `minimum`/`unsupported`/`supported` sao
# EXIGENCIA; `value` NAO e -- e o que uma imagem ou um cliente companheiro
# CONTEM naquela versao (`control_m_em_in_workbench_image`). As quatro moram no
# mesmo eixo porque a FORMA e a mesma (componente -> versao numa versao do
# Automation API), e a diferenca fica declarada na secao 4 do `.md`.
_CELULA_COMPONENTE = frozenset({"summary", "minimum", "unsupported", "supported", "value"})

# A ordem em que a exigencia e renderizada na forma canonica que o guard de
# drift compara contra a coluna *Exigencia* da tabela do `.md`. Ordem FIXA e nao
# `sorted()`: `sorted` mudaria a string publicada se alguem renomeasse uma chave,
# e o guard acusaria drift onde houve renomeacao.
_ORDEM_EXIGENCIA: tuple[str, ...] = ("value", "minimum", "unsupported", "supported")


def _path() -> Path:
    return safe_knowledge_file(knowledge_dir(), _RELATIVE)


def _documento() -> dict[str, Any]:
    """Le o YAML cru. Nao e cacheada de proposito, pela mesma razao de
    `runtime_matrix._documento`: as funcoes publicas tem cache proprio e cada
    uma limpa o seu, e um cache intermediario aqui sobreviveria ao
    `cache_clear()` delas dentro de um teste que apontou o `knowledge_dir` para
    outro lugar."""
    with _path().open("r", encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo) or {}


def _fora(vistas, permitidas: frozenset[str]) -> list[str]:
    return sorted(set(vistas) - permitidas)


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """A matriz inteira, validada contra os quatro vocabularios fechados.

    Devolve o documento como ele esta no YAML -- os dois eixos e as recusas --,
    porque as tres partes respondem perguntas diferentes e colapsa-las numa
    estrutura so faria `describe` ter de desfazer o colapso.
    """
    documento = _documento()
    caminho = _path()

    fora = _fora(documento, _DOCUMENTO)
    if fora:
        raise ControlMMatrixError(
            f"{caminho}: o documento declara {fora} -- o vocabulario e "
            f"{sorted(_DOCUMENTO)}, e chave nova e eixo inventado"
        )
    for chave in _DOCUMENTO_OBRIGATORIAS:
        if not documento.get(chave):
            raise ControlMMatrixError(
                f"{caminho}: bloco {chave!r} ausente ou vazio -- carregar assim "
                f"deixaria `describe` mudo em silencio"
            )

    covers = documento["covers"]
    fora = _fora(covers, frozenset({"from", "to"}))
    if fora or not covers.get("from") or not covers.get("to"):
        raise ControlMMatrixError(
            f"{caminho}: `covers` precisa de exatamente `from` e `to`; veio {covers!r}"
        )

    for slug, entrada in documento["capabilities"].items():
        if not isinstance(entrada, dict):
            raise ControlMMatrixError(f"{caminho}: capacidade {slug!r} nao e um mapa")
        fora = _fora(entrada, _CAPACIDADE)
        if fora:
            raise ControlMMatrixError(
                f"{caminho}: capacidade {slug!r} declara {fora} -- o vocabulario e "
                f"{sorted(_CAPACIDADE)}"
            )
        if not entrada.get("summary"):
            raise ControlMMatrixError(
                f"{caminho}: capacidade {slug!r} sem `summary` -- fronteira sem o que "
                f"ela delimita e numero solto"
            )
        presentes = [b for b in BOUNDARIES if entrada.get(b)]
        if not presentes:
            raise ControlMMatrixError(
                f"{caminho}: capacidade {slug!r} sem fronteira -- declare uma de "
                f"{list(BOUNDARIES)}, ou mova a afirmacao para `unresolved` com a razao"
            )

    for nome, versoes in documento["components"].items():
        if not isinstance(versoes, dict) or not versoes:
            raise ControlMMatrixError(
                f"{caminho}: componente {nome!r} precisa de ao menos uma versao"
            )
        for versao, celula in versoes.items():
            rotulo = f"{nome}[{versao}]"
            if not isinstance(celula, dict):
                raise ControlMMatrixError(f"{caminho}: {rotulo} nao e um mapa")
            fora = _fora(celula, _CELULA_COMPONENTE)
            if fora:
                raise ControlMMatrixError(
                    f"{caminho}: {rotulo} declara {fora} -- o vocabulario e "
                    f"{sorted(_CELULA_COMPONENTE)}"
                )
            if not celula.get("summary"):
                raise ControlMMatrixError(f"{caminho}: {rotulo} sem `summary`")
            if not any(c in celula for c in _ORDEM_EXIGENCIA):
                raise ControlMMatrixError(
                    f"{caminho}: {rotulo} sem exigencia nem valor -- declare uma de "
                    f"{list(_ORDEM_EXIGENCIA)}"
                )

    for chave, entrada in documento["unresolved"].items():
        if not isinstance(entrada, dict) or not entrada.get("reason"):
            raise ControlMMatrixError(
                f"{caminho}: recusa {chave!r} sem `reason` -- recusa sem razao e "
                f"omissao com nome bonito (ver a §20 do CLAUDE.md)"
            )
        fora = _fora(entrada, frozenset({"reason"}))
        if fora:
            raise ControlMMatrixError(f"{caminho}: recusa {chave!r} declara {fora}")

    return documento


@lru_cache(maxsize=1)
def covers() -> tuple[str, str]:
    """O intervalo `(from, to)` que esta matriz SUSTENTA.

    Publico porque a recusa de `describe` precisa NOMEA-LO -- "fora da faixa"
    sem dizer qual faixa e `UNKNOWN` mudo com outra grafia.
    """
    bloco = load()["covers"]
    return (str(bloco["from"]), str(bloco["to"]))


@lru_cache(maxsize=1)
def sources() -> tuple[str, ...]:
    """As URLs que a matriz declara como fonte.

    Existe para que o teste de fronteira possa exigir que todas estejam em
    `knowledge/sources.lock.json` -- URL solta na matriz, sem entrada no lock,
    nao teria hash nem data revalidados por `scripts/refresh_knowledge.py`.
    """
    return tuple(str(u) for u in load()["sources"])


def retrieved() -> str:
    return str(load()["retrieved"])


def _chave_de_versao(versao: str) -> tuple[int, ...]:
    """`9.0.21.200` -> `(9, 0, 21, 200)`, para comparar fronteira com versao.

    Comparacao por TUPLA DE INTEIROS e nao por string: `"9.0.22.100"` e
    lexicograficamente maior que `"9.0.22.060"`, mas `"9.0.21.100"` tambem seria
    maior que `"9.0.21.055"` -- e isso da certo por acidente enquanto os campos
    tem a mesma largura. `9.0.22.005` contra `9.0.22.010` ja depende do zero a
    esquerda estar la, e depender de zero a esquerda e depender de a BMC nunca
    publicar `9.0.22.5`.
    """
    partes = str(versao).strip().split(".")
    try:
        return tuple(int(p) for p in partes)
    except ValueError as exc:
        raise ControlMMatrixError(
            f"versao {versao!r} nao e uma sequencia de inteiros separados por ponto"
        ) from exc


def version_key(versao: str) -> tuple[int, ...]:
    """A chave de ordenacao de uma versao. Publica porque `descriptor.py`
    precisa da MESMA conta -- duas normalizacoes independentes divergiriam no
    primeiro caso de borda, e o caso de borda aqui e um zero a esquerda."""
    return _chave_de_versao(versao)


@lru_cache(maxsize=1)
def known_versions() -> tuple[str, ...]:
    """Toda versao da faixa que esta matriz conhece, em ordem crescente.

    Uma versao e conhecida quando ela e a fronteira de alguma capacidade, a
    versao de alguma celula de componente, OU uma recusa nomeada. As tres contam:
    `9.0.22.100` nao carrega afirmacao nenhuma e mesmo assim e conhecida, porque
    a matriz LEU a pagina daquela versao e o que ela achou foi nada -- e "li e
    nao achei" e resposta diferente de "nunca olhei".
    """
    documento = load()
    vistas: set[str] = set()
    for entrada in documento["capabilities"].values():
        for fronteira in BOUNDARIES:
            if entrada.get(fronteira):
                vistas.add(str(entrada[fronteira]))
    for versoes in documento["components"].values():
        vistas.update(str(v) for v in versoes)
    for chave in documento["unresolved"]:
        # As recusas misturam versao (`9.0.22.100`) e classe (`corrected_problems`)
        # no mesmo espaco de chaves, de proposito: as duas sao "isto a fonte nao
        # sustenta". So a que TEM forma de versao entra como versao conhecida.
        if _e_versao(chave):
            vistas.add(str(chave))
    piso, teto = covers()
    dentro = [
        v for v in vistas if _chave_de_versao(piso) <= _chave_de_versao(v) <= _chave_de_versao(teto)
    ]
    return tuple(sorted(dentro, key=_chave_de_versao))


def _e_versao(texto: str) -> bool:
    partes = str(texto).split(".")
    return len(partes) >= 3 and all(p.isdigit() for p in partes)


def _exigencia_canonica(celula: dict[str, Any]) -> str:
    """A forma canonica de uma celula de componente, para o guard de drift.

    O guard compara STRING contra a coluna *Exigencia* da tabela do `.md`. Um
    dicionario nao cabe numa celula de markdown, e escrever a string a mao nos
    dois lugares faria a terceira copia que o guard existe para nao ter.
    """
    partes: list[str] = []
    for chave in _ORDEM_EXIGENCIA:
        if chave not in celula:
            continue
        valor = celula[chave]
        if isinstance(valor, list):
            partes.append(f"{chave} {', '.join(str(v) for v in valor)}")
        elif isinstance(valor, bool):
            partes.append(f"{chave} {'true' if valor else 'false'}")
        else:
            partes.append(f"{chave} {valor}")
    return "; ".join(partes)


@lru_cache(maxsize=1)
def drift_view() -> dict[str, dict[str, Any]]:
    """Os dois eixos e as recusas ACHATADOS na forma que o guard de drift compara.

    POR QUE ACHATAR EM VEZ DE ESCREVER UM QUINTO MECANISMO.
    `tests/test_runtime_matrix_drift.py` ja e parametrizado por CELULA e ja le a
    tabela de markdown por cabecalho exato; o que ele precisa e de
    `{chave: {coluna: valor}}` dos dois lados. Os dois eixos cabem nessa forma
    sem perder nada -- a capacidade vira `{boundary, at_version, replaced_by}` e
    a celula de componente vira `{at_version, requirement}` --, entao acrescentar
    Control-M ali e acrescentar uma entrada em `PLATAFORMAS`, nao escrever um
    quinto parser de markdown para o mesmo formato de tabela.

    As tres familias de chave (slug de capacidade, nome de componente, chave de
    recusa) nao colidem, e cada uma preenche colunas diferentes -- o guard trata
    coluna ausente dos dois lados como o caso normal, que e a mesma semantica que
    ele ja da para `emr-6.4.0` sem Iceberg.
    """
    documento = load()
    achatada: dict[str, dict[str, Any]] = {}
    for slug, entrada in documento["capabilities"].items():
        fronteira = next(b for b in BOUNDARIES if entrada.get(b))
        linha = {"boundary": fronteira, "at_version": str(entrada[fronteira])}
        if entrada.get("replaced_by"):
            linha["replaced_by"] = str(entrada["replaced_by"])
        achatada[str(slug)] = linha
    for nome, versoes in documento["components"].items():
        for versao, celula in versoes.items():
            achatada[str(nome)] = {
                "at_version": str(versao),
                "requirement": _exigencia_canonica(celula),
            }
    for chave, entrada in documento["unresolved"].items():
        achatada[str(chave)] = {"unresolved_reason": str(entrada["reason"])}
    return achatada


# As colunas que `drift_view` pode preencher. E o `componentes` da entrada de
# `PLATAFORMAS` no guard, e esta aqui e nao la para nao virar lista paralela.
DRIFT_COLUMNS = frozenset(
    {"boundary", "at_version", "replaced_by", "requirement", "unresolved_reason"}
)
