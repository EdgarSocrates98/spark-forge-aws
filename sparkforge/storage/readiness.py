"""Cruza a matriz de feature com a matriz de runtime da PLATAFORMA.

O DEFEITO QUE ESTE MODULO EXISTE PARA FECHAR, e ele e de granularidade.

Ate 2026-09-01, `knowledge/storage/iceberg-feature-support.yaml` tinha uma
unica engine chamada `emr` e `sparkforge/facts/consumers.py` reconhecia um
unico servico chamado `emr`. O sub-projeto de EMR on EKS mediu que as TRES
plataformas publicam Iceberg diferente -- divergencia em 6 de 26 releases
comparaveis entre EC2 e EKS, com dois casos que decidem:

    emr-7.7.0   EC2 traz Iceberg 1.7.1-amzn-0; EKS traz 1.6.1-amzn-2. Minor
                diferente, e portanto aplicabilidade diferente de qualquer
                capacidade que tenha entrado entre as duas.
    emr-6.5.0   EC2 traz Iceberg 0.12.0; o EKS nao traz Iceberg NENHUM.

Uma resposta de prontidao dada para "EMR" esta errada para pelo menos uma das
tres, e o operador nao tem como saber qual. Celula que responde por tres coisas
que divergem e pior que celula ausente: ausencia e recusa, e aquela celula era
uma afirmacao.

POR QUE A VERSAO DE ICEBERG NAO FOI COPIADA PARA A MATRIZ DE FEATURE. Ela ja
existe em `knowledge/<plataforma>/runtime-matrix.yaml`, carregada por
`sparkforge/facts/runtime_matrix.py`. Uma coluna `iceberg` na matriz de feature
seria a TERCEIRA copia do mesmo fato -- e copia diverge na primeira atualizacao
de fonte, sempre. A matriz de feature declara `min_library_version`, que e uma
afirmacao sobre a BIBLIOTECA e nao sobre plataforma nenhuma, e este modulo
calcula o cruzamento.

O QUE O CRUZAMENTO PODE AFIRMAR, e o que ele nunca afirma. `min_library_version`
e LIMITE INFERIOR:

    biblioteca ANTERIOR ao minimo -> `UNSUPPORTED`. Uma biblioteca publicada
        antes da primeira release que nomeia a capacidade nao pode te-la. E o
        unico afirmativo que este modulo produz sozinho, e ele e negativo.
    biblioteca ATENDE o minimo -> o resultado e o que a CELULA DA ENGINE disser,
        que quase sempre e `UNKNOWN`. Atender o minimo e condicao necessaria e
        nunca suficiente: a AWS repackaga (`-amzn-N`) e pode desabilitar o que a
        upstream entrega, e nenhuma pagina lida nesta coleta nomeia feature de
        Iceberg v3 por nome para plataforma de EMR alguma.

Promover "atende o minimo" a `SUPPORTED` seria exatamente a inferencia que a
matriz inteira existe para impedir, so que por uma porta nova: a versao da
biblioteca no lugar da spec.

TRES RECUSAS COM NOME, e a diferenca entre elas importa:

    `iceberg_ausente_na_release`          a plataforma publica a release e NAO
                                          publica Iceberg nela (emr-6.5.0 no
                                          EKS). Nao saber que versao roda e
                                          diferente de saber que nao suporta --
                                          por isso `UNKNOWN`, nunca
                                          `UNSUPPORTED`.
    `variante_de_imagem_fora_da_matriz`   o limite declarado da granularidade.
                                          A linha de componentes do EMR on EKS
                                          e publicada por FAMILIA, e a propria
                                          fonte diz que `emr-7.7.0-java8-latest`
                                          nao tem Iceberg enquanto `emr-7.7.0`
                                          tem. Responder pela familia erraria
                                          essa celula, entao a resposta e a
                                          recusa com o nome da familia junto.
    `min_library_version_ausente`         a capacidade nao e nomeada por
                                          release nenhuma nas notas curadas
                                          lidas. Lacuna registrada, nao lacuna
                                          escondida.

ESTE MODULO NAO EXECUTA NADA. Mesma garantia estrutural de
`sparkforge/storage/upgrade.py`: nao importa cliente de AWS, nao importa Spark,
nao roda subprocesso. Ele le duas matrizes de conhecimento e compara tuplas.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sparkforge.facts import runtime_matrix
from sparkforge.storage import feature_support

# As plataformas com matriz de runtime versionada por release. Cada uma tem
# FONTE PROPRIA e nenhuma deriva das outras -- e por isso que sao tres entradas
# de EMR e nao uma com um parametro.
#
# `athena`, `redshift`, `trino`, `flink`, `bigquery` e companhia NAO estao aqui,
# e a ausencia e informacao: ninguem publica a versao de biblioteca Iceberg
# delas por release num formato que este repositorio leia. Perguntar por elas
# devolve `engine_sem_matriz_de_runtime`, que e uma recusa nomeada e nao um
# silencio.
PLATFORM_LOADERS: dict[str, Callable[[], dict[str, dict[str, Any]]]] = {
    "glue": runtime_matrix.load,
    "emr_ec2": runtime_matrix.load_emr,
    "emr_serverless": runtime_matrix.load_emr_serverless,
    "emr_eks": runtime_matrix.load_emr_eks,
}

# As tres plataformas em que `emr` se quebrou. Existe para que o codigo que
# precisa dizer "declare qual" nao reescreva a lista.
EMR_PLATFORMS = ("emr_ec2", "emr_serverless", "emr_eks")

# Vocabulario FECHADO de razao. Fechado pelo mesmo motivo que `SUPPORT_STATUS`
# e fechado: razao livre vira texto decorativo, e o ponto de nomear a recusa e
# poder testar que ela aconteceu -- e poder dizer, para cada uma, QUAL MEDIDA a
# destravaria.
REASONS = frozenset(
    {
        "engine_sem_matriz_de_runtime",
        "release_desconhecida",
        "variante_de_imagem_fora_da_matriz",
        "iceberg_ausente_na_release",
        "min_library_version_ausente",
        "biblioteca_anterior_ao_minimo",
        "biblioteca_atende_o_minimo",
    }
)


def _release_key(label: str) -> str:
    """`emr-7.7.0` e `7.7.0` sao a mesma release; a chave e a segunda.

    Espelha `sparkforge.facts.runtime_detect._emr_key`. Nao importa aquele
    modulo de proposito: `storage/` nao depende de `facts/runtime_detect`, que
    monta matrizes no nivel de modulo e arrasta a carga inteira junto.
    """
    texto = str(label).strip()
    return texto[4:] if texto.lower().startswith("emr-") else texto


def _family(chave: str) -> str:
    """`7.7.0-java8-latest` -> `7.7.0`. So para NOMEAR a familia na recusa.

    Nunca para responder por ela: a fonte declara que a variante de imagem pode
    divergir da familia na propria coluna que interessa aqui.
    """
    partes = chave.split("-")
    return partes[0] if partes else chave


def _comparavel(versao: str) -> tuple[int, ...]:
    """`1.7.1-amzn-0` -> `(1, 7, 1)`. O sufixo da AWS nao ordena.

    O valor CRU nunca e substituido por este na saida: `-amzn-N` e informacao
    real sobre o runtime -- descarta-la esconderia que a plataforma roda um fork
    da AWS, e nao o artefato da Apache.
    """
    base = str(versao).split("-", 1)[0].strip()
    partes: list[int] = []
    for pedaco in base.split("."):
        if not pedaco.isdigit():
            break
        partes.append(int(pedaco))
    return tuple(partes)


def library_version(engine: str, release: str) -> tuple[str, str]:
    """`(versao_crua, razao)` da biblioteca Iceberg daquela release.

    Devolve `("", razao)` quando nao ha versao a devolver, e a razao diz QUAL
    das tres ausencias aconteceu. Um `""` sem razao seria indistinguivel de uma
    plataforma que nao existe, e essa e a confusao que a separacao de `emr` em
    tres existiu para desfazer.
    """
    carregar = PLATFORM_LOADERS.get(engine)
    if carregar is None:
        return "", "engine_sem_matriz_de_runtime"

    matriz = carregar()
    chave = _release_key(release)
    if chave not in matriz:
        familia = _family(chave)
        if familia != chave and familia in matriz:
            return "", "variante_de_imagem_fora_da_matriz"
        return "", "release_desconhecida"

    versao = matriz[chave].get("iceberg")
    if not versao:
        return "", "iceberg_ausente_na_release"
    return str(versao), ""


def readiness(feature: str, engine: str, release: str) -> dict[str, Any]:
    """Prontidao de uma feature numa release CONCRETA de uma plataforma.

    A saida carrega o que sustenta o veredito, e nao so o veredito: a versao de
    biblioteca medida, o minimo declarado, a razao no vocabulario fechado e a
    celula da engine consultada. Um status sem isso seria uma palavra que
    ninguem consegue conferir -- e a matriz existe justamente para que suporte
    seja conferivel.
    """
    # A celula e consultada pela chave NORMALIZADA da release, e nao pela
    # curinga: o Glue distingue `6.0` de `5.1` por escrito, e perguntar com `*`
    # apagaria a unica engine que tem celula afirmativa por nome de feature.
    # `cell()` ja cai na curinga quando a fonte nao qualifica por versao.
    celula = feature_support.cell(feature, engine, _release_key(release))
    minimo = feature_support.min_library_version(feature)
    minimo_valor = str(minimo["value"]) if minimo else ""

    versao, razao = library_version(engine, release)
    if razao:
        return _resultado(feature, engine, release, "UNKNOWN", razao, "", minimo_valor, celula)

    if not minimo:
        return _resultado(
            feature,
            engine,
            release,
            "UNKNOWN",
            "min_library_version_ausente",
            versao,
            "",
            celula,
        )

    if _comparavel(versao) < _comparavel(minimo_valor):
        return _resultado(
            feature,
            engine,
            release,
            "UNSUPPORTED",
            "biblioteca_anterior_ao_minimo",
            versao,
            minimo_valor,
            celula,
        )

    # Atender o minimo NAO promove nada. O resultado e o que a celula da engine
    # disser -- e ela quase sempre diz `UNKNOWN`, que continua sendo a resposta
    # honesta enquanto nenhuma pagina da AWS nomear a feature para a plataforma.
    return _resultado(
        feature,
        engine,
        release,
        celula["status"],
        "biblioteca_atende_o_minimo",
        versao,
        minimo_valor,
        celula,
    )


def _resultado(
    feature: str,
    engine: str,
    release: str,
    status: str,
    reason: str,
    library: str,
    minimo: str,
    celula: dict[str, Any],
) -> dict[str, Any]:
    if reason not in REASONS:
        raise AssertionError(f"razao fora do vocabulario declarado: {reason!r}")
    return {
        "feature": feature,
        "engine": engine,
        "release": release,
        "status": status,
        "reason": reason,
        "library_version": library,
        "min_library_version": minimo,
        "cell_status": celula["status"],
        "source": celula.get("source", ""),
        "note": celula.get("note", ""),
    }


def diverges(feature: str, release: str, engines: tuple[str, ...] = EMR_PLATFORMS) -> bool:
    """As plataformas respondem DIFERENTE para esta feature nesta release?

    O contrafactual da granularidade em uma linha. Enquanto `emr` era uma engine
    so, esta funcao nao podia nem ser escrita -- nao havia duas coisas para
    comparar. Ela existe para que o teste que prova a separacao nao reimplemente
    a comparacao e, com isso, deixe de ver a proxima divergencia.
    """
    respostas = {readiness(feature, engine, release)["status"] for engine in engines}
    return len(respostas) > 1
