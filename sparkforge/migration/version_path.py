"""Expande um par origem/alvo nos degraus intermediarios da matriz.

POR QUE ISSO EXISTE SEPARADO DO PLANO DE EXECUCAO: o §6.2 do prompt de migracao
distingue migracao direta OPERACIONAL de analise CUMULATIVA obrigatoria. Quem
migra pode saltar 4.0 para 6.0 num movimento so; quem ANALISA nao pode, porque
os breaking changes se acumulam degrau a degrau e um salto esconde os do meio.

O modulo nao conhece regra, fact nem finding. Ele responde uma pergunta so:
quais degraus existem entre estas duas versoes, segundo a matriz DAQUELA
plataforma.

AS QUATRO PLATAFORMAS, E A ORDEM QUE VEM DA MATRIZ (D-1 da spec de EMR)

Ate o sub-projeto 3 este modulo so sabia de Glue, e a ordem vinha de
`runtime_matrix.known_versions()`. Agora ele atende as quatro, e a ordem
continua vindo da MATRIZ -- `release_descriptor.known_releases(platform)`, que
le o YAML de `knowledge/` daquela plataforma. Nao ha lista nova em codigo: e a
mesma disciplina que tirou `EMR_MATRIX` de dentro do `.py` no sub-projeto 2, e
o teste `test_nenhum_par_de_versao_aparece_no_codigo_do_motor` continua sendo o
guarda dela.

AS DUAS SERIES, E OS ROTULOS QUE NAO SAO VERSAO

EMR tem duas series vivas (6.x e 7.x) e o caminho que as atravessa e LEGITIMO:
`6.15.0 -> 7.5.0` e a pergunta literal de uma migracao real, e a ordem numerica
por segmento ja a responde sem caso especial.

O que nao e ordenavel sao os rotulos fora do padrao de versao: `spark-8.0.0`
(EKS e Serverless) e `spark-8.0-preview` (Serverless). Eles NAO entram na
ordem, e um caminho que os cite e RECUSADO PELO NOME -- nunca ordenado
alfabeticamente. Ordenacao alfabetica colocaria `spark-8.0-preview` ANTES de
`spark-8.0.0` (o `-` vem antes do `.` em ASCII) e as duas depois de qualquer
`7.x`, o que e verdade por acidente de escrita e nao por medida: a fonte nao
publica ordem entre a previa e a release, e inventa-la aqui produziria um
degrau que ninguem pode migrar. Recusa com nome, e o operador decide.

A GRAFIA: `emr-7.7.0` E `7.7.0` SAO A MESMA RELEASE

A pagina do EMR escreve `emr-7.7.0` no titulo e `7.7.0` na tabela. O
sub-projeto 2 resolveu aceitando as duas grafias e emitindo UMA -- a chave da
matriz --, e este modulo faz o mesmo pela mesma funcao
(`release_descriptor.normalize_release`), para que o degrau emitido seja
conferivel contra `known_releases()` sem traducao no meio.
"""
from __future__ import annotations

import re

from sparkforge.migration import release_descriptor

# Plataforma default de `steps` e `assess`. Nao ha default para o PAR de
# versoes -- ver o docstring de `assessment.assess` --, mas ha para a
# plataforma: `migrate glue` foi a interface publicada antes das quatro
# existirem, e obrigar `platform=` em quem ja chamava trocaria uma extensao por
# uma quebra sem nada de util em troca.
DEFAULT_PLATFORM = "glue"

# Rotulo ORDENAVEL: so digitos e pontos. `7.13.0`, `6.11.1` e `5.1` passam;
# `spark-8.0.0` e `spark-8.0-preview` nao. Deliberadamente estrito -- uma
# heuristica que tentasse extrair numero de dentro do rotulo transformaria a
# recusa nomeada numa ordenacao adivinhada.
_PADRAO_DE_VERSAO = re.compile(r"^[0-9]+(?:\.[0-9]+)*$")


def _ordenavel(rotulo: str) -> bool:
    return bool(_PADRAO_DE_VERSAO.match(rotulo))


def _chave_de_ordem(rotulo: str) -> tuple[int, ...]:
    return tuple(int(parte) for parte in rotulo.split("."))


def platforms() -> tuple[str, ...]:
    """As quatro plataformas, na ordem fixa do modelo de release."""
    return release_descriptor.PLATFORMS


def ordered_releases(platform: str = DEFAULT_PLATFORM) -> list[str]:
    """As releases ORDENAVEIS daquela plataforma, em ordem crescente.

    A fonte da ordem e a matriz, e `known_releases` a devolve na ordem
    EDITORIAL da fonte (mais nova primeiro). Ordem editorial nao e ordem de
    caminho: quem migra sobe. Ordenar aqui, por segmento numerico, e o que faz
    `6.11.1` vir depois de `6.11.0` e `7.0.0` depois de `6.15.0` -- as duas
    coisas que uma ordenacao textual erraria.

    Rotulo fora do padrao de versao NAO aparece: ele nao tem posicao. Ver
    `out_of_pattern`.
    """
    conhecidas = release_descriptor.known_releases(platform)
    return sorted((r for r in conhecidas if _ordenavel(r)), key=_chave_de_ordem)


def out_of_pattern(platform: str = DEFAULT_PLATFORM) -> tuple[str, ...]:
    """Os rotulos daquela plataforma que nao sao versao, na ordem da matriz."""
    conhecidas = release_descriptor.known_releases(platform)
    return tuple(r for r in conhecidas if not _ordenavel(r))


def _recusa_por_nome(platform: str, rotulo: str) -> str:
    fora = out_of_pattern(platform)
    return (
        f"rotulo {rotulo!r} da matriz de {platform} esta fora do padrao de versao e "
        f"por isso nao tem posicao num caminho de migracao. Recusado pelo NOME, nao "
        f"ordenado: ordenacao alfabetica o colocaria entre releases por acidente de "
        f"escrita, e a fonte nao publica ordem entre a previa e a release. Rotulos "
        f"fora do padrao nesta matriz: {', '.join(fora)}. Compare-os com "
        f"`release diff`, que nao precisa de ordem, ou nomeie o par ja resolvido"
    )


def steps(
    source: str, target: str, platform: str = DEFAULT_PLATFORM
) -> list[tuple[str, str]]:
    """Os degraus adjacentes de `source` ate `target`, na ordem da matriz.

    `source` e `target` aceitam as duas grafias da fonte (`emr-7.5.0` e
    `7.5.0`) e saem SEMPRE na chave da matriz -- a mesma que `known_releases`
    devolve --, para que o degrau emitido seja conferivel sem traducao.
    """
    if platform not in release_descriptor.PLATFORMS:
        raise ValueError(
            f"plataforma {platform!r} fora das quatro que este motor conhece: "
            f"{', '.join(release_descriptor.PLATFORMS)}"
        )

    conhecidas = ordered_releases(platform)
    fora = set(out_of_pattern(platform))
    resolvidas: list[str] = []
    for rotulo in (source, target):
        chave = release_descriptor.normalize_release(platform, rotulo)
        if chave in fora:
            raise ValueError(_recusa_por_nome(platform, chave))
        if chave not in conhecidas:
            raise ValueError(
                f"versao {chave!r} fora da matriz de {platform}; "
                f"conhecidas: {', '.join(conhecidas)}"
            )
        resolvidas.append(chave)

    inicio = conhecidas.index(resolvidas[0])
    fim = conhecidas.index(resolvidas[1])
    if fim < inicio:
        raise ValueError(
            f"alvo anterior a origem: {resolvidas[0]!r} -> {resolvidas[1]!r}"
        )
    return [(conhecidas[i], conhecidas[i + 1]) for i in range(inicio, fim)]
