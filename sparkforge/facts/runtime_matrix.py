"""Carrega a matriz de runtime do AWS Glue como dado, nao como constante.

Versao de Glue e fato EXTERNO -- muda por decisao da AWS, nao deste
repositorio. Antes desta entrega o valor vivia compilado em
`sparkforge/facts/runtime_detect.py` (GLUE_MATRIX) sem fonte nem data de
consulta; agora mora em `knowledge/glue/runtime-matrix.yaml`, ao lado dos
demais fatos externos vigiados por `knowledge/sources.lock.json`. Cache com
`lru_cache` porque o arquivo nao muda durante a vida do processo e varias
regras consultam a matriz por execucao.

RESOLUCAO DE CAMINHO: por que este modulo usa `sparkforge.knowledge_ref`, e
nao a sua propria conta de `parents[N]`.

A primeira versao deste arquivo (Fase SF-MIG, Task 1) computava
`ROOT = Path(__file__).resolve().parents[2]` e lia
`ROOT / "knowledge" / "glue" / "runtime-matrix.yaml"`. Isso funciona no
checkout de desenvolvimento -- `sparkforge/facts/runtime_matrix.py` fica dois
niveis abaixo da raiz do repositorio, onde `knowledge/` mora de verdade. Mas
`pyproject.toml` empacota `knowledge/` DENTRO do pacote instalado
(`[tool.hatch.build.targets.wheel.force-include]`: `"knowledge" =
"sparkforge/knowledge"`), entao no wheel instalado o arquivo esta em
`<site-packages>/sparkforge/knowledge/glue/runtime-matrix.yaml` -- um nivel
a mais de profundidade do que a conta original alcancava. `parents[2]` a
partir de `<site-packages>/sparkforge/facts/runtime_matrix.py` cai em
`<site-packages>`, nao em `<site-packages>/sparkforge`, e a leitura procurava
`knowledge/` no lugar errado.

Isso ficou latente na Task 1: nada chamava `load()` na importacao do modulo,
entao o bug so apareceria se algum consumidor chamasse a funcao rodando de
um pacote instalado. A Task 2 (`runtime_detect.py`) passou a montar
`GLUE_MATRIX` no NIVEL DE MODULO, chamando `load()` na propria importacao --
e isso transformou um bug latente em `import sparkforge.facts.runtime_detect`
quebrando incondicionalmente num wheel instalado. Reproduzido e confirmado:
build do wheel, instalacao num venv limpo, `import
sparkforge.facts.runtime_detect` -> `FileNotFoundError` em
`<site-packages>/knowledge/glue/runtime-matrix.yaml`.

`sparkforge/knowledge_ref.py` ja resolve exatamente este problema, para
exatamente este diretorio, desde a Fase 3a -- "knowledge/ passou a ser
embarcado no artefato e nenhum codigo sabia encontra-lo". A ordem de
precedencia (env var `SPARKFORGE_KNOWLEDGE` -> raiz do repo -> `parent` do
proprio modulo dentro do pacote) e a MESMA que `sparkforge/rules/loader.py`
usa para `rules/catalog`, e tem teste dedicado para o caso de pacote
instalado (`tests/test_knowledge_ref.py::
test_falls_back_to_the_package_dir_when_no_repo_root_exists`). Reimplementar
essa resolucao aqui -- como a Task 1 fez -- e reproduzir o bug que o modulo
já existe para fechar. Este modulo usa `knowledge_dir()`/`safe_knowledge_file()`
em vez disso.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file


class RuntimeMatrixError(ValueError):
    """Matriz de runtime ausente, vazia ou com evidencia mal declarada.

    Uma matriz vazia carregaria em silencio e derrubaria toda regra com
    escopo de versao sem aviso -- o mesmo modo de falha que este motor
    recusa em qualquer outro extrator. Melhor estourar aqui do que deixar
    regra sumir por ausencia de dado que parecia presente.
    """


# Qualidade da fonte, do mais autoritativo ao menos. Vocabulario FECHADO: um
# `source_type` livre viraria etiqueta decorativa em duas semanas, e o ponto
# de classificar fonte e poder dizer POR QUE uma discordancia entre duas
# delas nao se resolve sozinha. Documentacao tecnica e spec descrevem o que o
# produto FAZ; anuncio descreve o que ele foi LANCADO fazendo, e os dois
# divergem quando um deles e corrigido depois da publicacao e o outro nao.
SOURCE_TYPES = frozenset(
    {
        "OFFICIAL_TECHNICAL_DOC",
        "OFFICIAL_RELEASE_DOC",
        "OFFICIAL_BLOG",
        "UPSTREAM_SPEC",
        "UPSTREAM_RELEASE",
        "PROVIDER_DOC",
        "COMMUNITY",
    }
)

# Estados que este carregador sabe ENFORCAR hoje. `STALE` e `UNVERIFIED`
# ficam de fora de proposito: os dois sao afirmacoes sobre FRESCOR, e frescor
# depende de um TTL por dominio que este repositorio ainda nao tem como dado
# (a lacuna esta registrada em `docs/harness/GLUE6-GAP.md`, secao 1). Aceitar
# aqui um estado que nenhum mecanismo produz seria declarar vocabulario sem
# consumidor -- a mesma classe de defeito que o `blocked_on` do catalogo de
# regras existe para tornar visivel em vez de fingir cobertura.
CLAIM_STATUS = frozenset({"VERIFIED", "CONFLICTING", "UNRESOLVED"})

# Estados em que o componente NAO recebe valor resolvido. Fail-closed: sem a
# chave no runtime, `sparkforge/rules/version_scope.py::in_scope` reprova a
# regra guardada por ela e o motor a reporta como pulada, com motivo. O
# oposto -- escolher uma das versoes em disputa para nao deixar a regra muda
# -- e exatamente o que a secao 2 de `prompt_glue_harness.md` proibe: julgar
# com um numero que duas fontes oficiais nao confirmam junto.
_SEM_VALOR_RESOLVIDO = frozenset({"CONFLICTING", "UNRESOLVED"})


def _matrix_path() -> Path:
    return safe_knowledge_file(knowledge_dir(), "glue/runtime-matrix.yaml")


# A matriz do EMR Serverless mora ao lado, no mesmo formato de dado externo, e
# NAO substitui a `EMR_MATRIX` de EMR on EC2: sao plataformas diferentes com
# fontes diferentes, e a pagina `knowledge/emr-serverless/runtime-matrix.md`
# mede que tres das quatro colunas da matriz de EC2 nao tem fonte nenhuma do
# lado do Serverless. Ver o cabecalho do proprio YAML.
_EMR_SERVERLESS_RELATIVE = "emr-serverless/runtime-matrix.yaml"


def _emr_serverless_path() -> Path:
    return safe_knowledge_file(knowledge_dir(), _EMR_SERVERLESS_RELATIVE)


def _sources_lock_path() -> Path:
    return safe_knowledge_file(knowledge_dir(), "sources.lock.json")


def _documento(caminho: Path) -> dict[str, Any]:
    """Le um YAML de matriz cru. Nao e cacheada de proposito: as funcoes
    publicas tem cache proprio, e cada uma limpa o seu -- um cache intermediario
    aqui sobreviveria ao `cache_clear()` delas e devolveria a matriz do
    repositorio real dentro de um teste que apontou o `knowledge_dir` para outro
    lugar."""
    with caminho.open("r", encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo) or {}


def _versoes(caminho: Path) -> dict[str, dict[str, Any]]:
    versoes = _documento(caminho).get("versions")
    if not versoes:
        raise RuntimeMatrixError(
            f"{caminho}: bloco 'versions' ausente ou vazio -- "
            "toda regra com escopo de versao ficaria muda em silencio"
        )
    return versoes


def _read() -> dict[str, dict[str, Any]]:
    """As versoes do Glue, cruas. Ver `_documento` sobre por que nao ha cache."""
    return _versoes(_matrix_path())


def _validar_evidencia(versao: str, componente: str, registro: dict[str, Any]) -> set[str]:
    """Valida um componente na forma longa e devolve os valores distintos que
    as fontes afirmam.

    As duas invariantes que dao sentido ao mecanismo, e que existem em CODIGO
    porque disciplina de quem edita YAML nao sobrevive a um ano:

    1. `VERIFIED` com duas fontes afirmando valores diferentes e proibido. E a
       regra da secao 1 do prompt -- "nunca transformar CONFLICTING em
       VERIFIED" -- e sem gate ela e so uma frase: a forma pratica de violar
       nao e mentir, e editar o valor de uma linha e esquecer a outra.
    2. `CONFLICTING` com todas as fontes concordando tambem e proibido.
       Conflito inventado gasta a atencao de quem le exatamente como conflito
       escondido a desperdica -- e, pior, deixa o componente sem valor
       resolvido, apagando em silencio toda regra guardada por ele.
    """
    status = registro.get("status")
    if status not in CLAIM_STATUS:
        raise RuntimeMatrixError(
            f"{versao}.{componente}: status {status!r} fora de {sorted(CLAIM_STATUS)} "
            "-- STALE e UNVERIFIED ainda nao tem mecanismo que os produza"
        )

    claims = registro.get("claims")
    if not claims:
        raise RuntimeMatrixError(
            f"{versao}.{componente}: forma longa sem `claims` -- um status sem "
            "evidencia por tras e opiniao com nome de fato"
        )

    valores: set[str] = set()
    for claim in claims:
        for campo in ("value", "source", "source_type", "retrieved"):
            if not claim.get(campo):
                raise RuntimeMatrixError(f"{versao}.{componente}: claim sem `{campo}`")
        if claim["source_type"] not in SOURCE_TYPES:
            raise RuntimeMatrixError(
                f"{versao}.{componente}: source_type {claim['source_type']!r} fora de "
                f"{sorted(SOURCE_TYPES)}"
            )
        valores.add(str(claim["value"]))

    if status == "VERIFIED" and len(valores) > 1:
        raise RuntimeMatrixError(
            f"{versao}.{componente}: status VERIFIED com fontes afirmando "
            f"{sorted(valores)} -- discordancia entre fontes e CONFLICTING, e "
            "CONFLICTING nunca vira VERIFIED por edicao de status"
        )
    if status == "CONFLICTING" and len(valores) == 1:
        raise RuntimeMatrixError(
            f"{versao}.{componente}: status CONFLICTING com todas as fontes "
            f"afirmando {sorted(valores)[0]!r} -- conflito inventado apaga em "
            "silencio toda regra guardada por este componente"
        )
    return valores


@lru_cache(maxsize=1)
def load() -> dict[str, dict[str, Any]]:
    """Matriz de versoes do Glue RESOLVIDA, indexada pela versao (ex.: "5.1").

    Componente declarado na forma curta (`spark: "4.1.1"`) passa direto.
    Componente na forma longa (um registro com `status` e `claims`) vira o
    valor unico que as fontes confirmam quando o status e `VERIFIED`, e
    simplesmente NAO APARECE quando o status retem o valor -- ver
    `_SEM_VALOR_RESOLVIDO`. Quem precisa da evidencia por tras chama
    `evidence()`.
    """
    resolvida: dict[str, dict[str, Any]] = {}
    for versao, linha in _read().items():
        resolvida[versao] = {}
        for componente, valor in linha.items():
            if not isinstance(valor, dict) or "claims" not in valor:
                resolvida[versao][componente] = valor
                continue
            valores = _validar_evidencia(versao, componente, valor)
            if valor["status"] in _SEM_VALOR_RESOLVIDO:
                continue
            resolvida[versao][componente] = valores.pop()
    return resolvida


@lru_cache(maxsize=1)
def evidence() -> dict[str, dict[str, dict[str, Any]]]:
    """Componentes declarados na forma longa, por versao, com claims e status.

    Existe separada de `load()` porque as duas respondem perguntas diferentes:
    `load()` responde "com que versao eu julgo", e precisa reter o valor em
    disputa; esta responde "o que as fontes dizem, e por que isso nao virou
    um valor", e precisa mostrar a disputa inteira. Componente na forma curta
    nao aparece aqui -- ele nao tem disputa a relatar.
    """
    detalhe: dict[str, dict[str, dict[str, Any]]] = {}
    for versao, linha in _read().items():
        for componente, valor in linha.items():
            if not isinstance(valor, dict) or "claims" not in valor:
                continue
            _validar_evidencia(versao, componente, valor)
            detalhe.setdefault(versao, {})[componente] = valor
    return detalhe


def conflicting() -> list[tuple[str, str]]:
    """Pares `(versao, componente)` cujo valor esta retido por disputa.

    A lista que um relatorio de migracao precisa para dizer "este eixo nao foi
    julgado, e por que" em vez de omiti-lo.
    """
    return sorted(
        (versao, componente)
        for versao, componentes in evidence().items()
        for componente, registro in componentes.items()
        if registro["status"] in _SEM_VALOR_RESOLVIDO
    )


@lru_cache(maxsize=1)
def watched_sources() -> frozenset[str]:
    """Retorna as URLs vigiadas em `knowledge/sources.lock.json`.

    Usado para validar que toda fonte citada na matriz e uma fonte que o
    mecanismo de procedencia do repositorio efetivamente rastreia -- uma
    URL solta na matriz, sem entrada no lock, nao teria hash nem data
    revalidados por `scripts/refresh_knowledge.py`.
    """
    with _sources_lock_path().open("r", encoding="utf-8") as arquivo:
        lock = json.load(arquivo)
    return frozenset(lock.get("sources", {}).keys())


def known_versions() -> list[str]:
    """Versoes de Glue conhecidas pela matriz, em ordem crescente."""
    return sorted(load().keys(), key=lambda v: tuple(int(p) for p in v.split(".")))


# --------------------------------------------------------------------------- #
# EMR Serverless
# --------------------------------------------------------------------------- #

# Vocabulario FECHADO de componente, pelo mesmo motivo de `SOURCE_TYPES`: a
# unica forma pratica de esta matriz voltar a inventar eixo e alguem acrescentar
# uma chave `python:` numa linha porque "o EC2 tem". Chave fora daqui estoura na
# carga, com o nome do componente e da release.
EMR_SERVERLESS_COMPONENTS = frozenset({"spark", "iceberg"})


@lru_cache(maxsize=1)
def load_emr_serverless() -> dict[str, dict[str, str]]:
    """Matriz do EMR Serverless, indexada pelo release label SEM o prefixo
    `emr-` (`"7.5.0"`, `"spark-8.0.0"`) -- a mesma normalizacao de
    `sparkforge.facts.runtime_detect._emr_key`.

    So a forma curta (`spark: "3.5.2"`). A forma longa com `claims` existe na
    matriz do Glue porque la houve disputa entre fontes oficiais a registrar;
    aqui nao ha celula em disputa -- ha celula AUSENTE, que e outra coisa e ja
    tem semantica propria neste motor (chave que nao existe faz `in_scope`
    reprovar o eixo, e a regra e pulada por ausencia). Um registro em forma
    longa aqui seria vocabulario sem consumidor, entao ele estoura em vez de
    carregar meio entendido.
    """
    caminho = _emr_serverless_path()
    resolvida: dict[str, dict[str, str]] = {}
    for release, linha in _versoes(caminho).items():
        if not isinstance(linha, dict):
            raise RuntimeMatrixError(
                f"{caminho}: release {release!r} nao e um mapa de componentes"
            )
        fora = sorted(set(linha) - EMR_SERVERLESS_COMPONENTS)
        if fora:
            raise RuntimeMatrixError(
                f"{caminho}: release {release!r} declara {fora} -- a fonte do EMR "
                f"Serverless publica apenas {sorted(EMR_SERVERLESS_COMPONENTS)}, e "
                f"componente sem fonte e eixo inventado (ver o cabecalho do YAML)"
            )
        for componente, valor in linha.items():
            if not isinstance(valor, str) or not valor.strip():
                raise RuntimeMatrixError(
                    f"{caminho}: {release}.{componente} = {valor!r} -- valor vazio "
                    f"afirmaria leitura que nao aconteceu; omita a chave"
                )
        resolvida[str(release)] = {c: str(v) for c, v in linha.items()}
    return resolvida


@lru_cache(maxsize=1)
def emr_serverless_sources() -> tuple[str, ...]:
    """As URLs que a matriz do Serverless declara como fonte.

    Existe para que `tests/test_emr_serverless_runtime_boundary.py` possa exigir
    que todas estejam em `knowledge/sources.lock.json` -- URL solta na matriz,
    sem entrada no lock, nao teria hash nem data revalidados por
    `scripts/refresh_knowledge.py`.
    """
    fontes = _documento(_emr_serverless_path()).get("sources") or []
    return tuple(str(url) for url in fontes)
