"""Carrega o eixo de versao de Lake Formation como DADO, nao como prosa.

NAO E UM EXTRATOR, e por isso nao tem `EMITTED_KINDS`. Mesma natureza de
`runtime_matrix.py`, `pricing.py` e `cloudwatch_retention.py`: carregador de
conhecimento externo, no diretorio dos extratores por vizinhanca de tema e nao
por papel. As varreduras que contam extratores excluem os sete carregadores por
ausencia de `EMITTED_KINDS`.

POR QUE ELE EXISTE, e ele nao duplica `runtime_matrix.py`. Aquele guarda VERSAO
DE COMPONENTE por runtime -- Spark 3.5.6, Iceberg 1.10.0. Este guarda
CAPACIDADE: "este runtime escreve sob FGAC?", "qual e o filesystem S3 default?".
As duas perguntas nao se deduzem uma da outra, e e a segunda que decide
diagnostico nesta area.

Ate 2026-09-09 as respostas existiam SO como tabela markdown na §0 de
`knowledge/glue/lakeformation-fgac.md`. Consequencia medida: nenhum verbo as
lia, nenhum gate as conferia, e a matriz que governa o diagnostico de uma area
de 21 regras nao era legivel por maquina.

TRES ESTADOS, E O TERCEIRO NAO E "FALSO". `supported`, `not_supported`,
`not_declared` e `not_applicable` -- a diferenca entre os dois ultimos e a que
este modulo existe para preservar. `not_declared` significa "nenhuma pagina
vigiada diz", e devolver `False` ali seria a mesma inferencia que a regra 20 do
`CLAUDE.md` recusa.

`quote` VAZIA com status `supported` nao e defeito: algumas celulas da tabela da
AWS sao tabela, nao sentenca, e nao ha frase citavel. A celula carrega `nota`
dizendo isso, e `citada()` as separa de quem tem frase -- e ela que responde
"quantas destas afirmacoes tem frase da fonte por tras?".
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file

_RELATIVE = "glue/lakeformation-matrix.yaml"

# Os quatro estados que uma celula de capacidade pode ter. Fechado de proposito:
# um valor novo no YAML derruba `load()` em vez de viajar calado ate um `if` que
# nao o previa.
STATUS_VALIDOS = frozenset({"supported", "not_supported", "not_declared", "not_applicable"})

# Os dois que EXIGEM fonte. `not_declared` nao pode ter -- se tivesse, nao seria
# nao declarado --, e `not_applicable` afirma que a capacidade nao existia, o que
# se sustenta pela ausencia dela na propria matriz.
EXIGEM_FONTE = frozenset({"supported", "not_supported"})


def _path() -> Path:
    return safe_knowledge_file(knowledge_dir(), _RELATIVE)


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """O documento inteiro, validado.

    Levanta `ValueError` quando o YAML declara status fora de `STATUS_VALIDOS`,
    quando uma celula que exige fonte nao a tem, ou quando a fonte nomeada nao
    esta no bloco `fontes`. Validar na carga e o que impede que uma celula
    escrita a mao com `source: fgacc` (typo) passe por afirmacao com fonte.
    """
    with _path().open("r", encoding="utf-8") as arquivo:
        documento = yaml.safe_load(arquivo) or {}

    fontes = documento.get("fontes") or {}
    runtimes = documento.get("runtimes") or {}
    eixos = {e["id"] for e in (documento.get("eixos") or [])}

    problemas: list[str] = []
    for runtime, celulas in runtimes.items():
        for eixo, celula in (celulas or {}).items():
            if eixo not in eixos:
                problemas.append(f"{runtime}.{eixo}: eixo nao declarado no bloco `eixos`")
                continue
            status = (celula or {}).get("status")
            if status not in STATUS_VALIDOS:
                problemas.append(f"{runtime}.{eixo}: status {status!r} fora de STATUS_VALIDOS")
                continue
            if status in EXIGEM_FONTE:
                fonte = (celula or {}).get("source")
                if not fonte:
                    problemas.append(f"{runtime}.{eixo}: status {status!r} sem `source`")
                elif fonte not in fontes:
                    problemas.append(f"{runtime}.{eixo}: `source` {fonte!r} nao esta em `fontes`")
            elif (celula or {}).get("source"):
                problemas.append(
                    f"{runtime}.{eixo}: status {status!r} nao pode carregar `source`"
                )

    # Todo eixo declarado tem de existir em TODO runtime. Celula faltando e o
    # modo de falha que uma tabela markdown esconde bem: a coluna some e a
    # leitura assume o valor da coluna vizinha.
    for runtime, celulas in runtimes.items():
        faltando = sorted(eixos - set((celulas or {}).keys()))
        if faltando:
            problemas.append(f"{runtime}: eixos sem celula: {faltando}")

    if problemas:
        raise ValueError(
            "knowledge/glue/lakeformation-matrix.yaml invalido:\n  " + "\n  ".join(problemas)
        )
    return documento


@lru_cache(maxsize=1)
def known_runtimes() -> tuple[str, ...]:
    """As versoes de Glue que a matriz cobre, em ordem crescente."""
    return tuple(sorted((load().get("runtimes") or {}).keys(), key=_ordem))


def _ordem(versao: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in versao.split("."))
    except ValueError:
        return (0,)


@lru_cache(maxsize=1)
def eixos() -> tuple[dict[str, Any], ...]:
    return tuple(load().get("eixos") or [])


def capability(runtime: str, eixo: str) -> dict[str, Any] | None:
    """A celula, ou `None` quando o runtime ou o eixo nao existem na matriz.

    `None` e a resposta honesta para "Glue 6.0 escreve sob FGAC?": a matriz nao
    cobre o 6.0, e devolver `not_declared` confundiria "a pagina nao diz" com
    "nao lemos a pagina".
    """
    celulas = (load().get("runtimes") or {}).get(runtime)
    if not celulas:
        return None
    return celulas.get(eixo)


def citada(runtime: str, eixo: str) -> bool:
    """A celula tem FRASE da fonte, e nao so a URL dela.

    Separa as celulas sustentadas por sentenca citavel das que vem de tabela da
    propria AWS -- que tem fonte e nao tem frase. As duas sao afirmacoes com
    fonte; so a primeira e citavel num relatorio.
    """
    celula = capability(runtime, eixo) or {}
    return bool((celula.get("quote") or "").strip())


def limites_declarados() -> tuple[str, ...]:
    return tuple(load().get("limites_declarados") or [])


def watched_sources() -> frozenset[str]:
    """As URLs que esta matriz cita, para a watchlist de `refresh_knowledge.py`."""
    return frozenset((load().get("fontes") or {}).values())


def cache_clear() -> None:
    """Limpa os caches deste modulo. Chamado por teste que aponta
    `knowledge_dir` para outro lugar -- sem isso o segundo teste leria a matriz
    do primeiro."""
    load.cache_clear()
    known_runtimes.cache_clear()
    eixos.cache_clear()
