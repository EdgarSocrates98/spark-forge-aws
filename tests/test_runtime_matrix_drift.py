"""Guard de drift das QUATRO matrizes de runtime, com um mecanismo so.

O PROBLEMA QUE ESTE ARQUIVO FECHA. Cada `knowledge/<plataforma>/runtime-matrix`
existe em dois lugares: a pagina `.md`, que e onde a prosa explica o que a fonte
NAO sustenta, e o `.yaml`, que e o espelho executavel que o motor carrega. Nada
obriga os dois a concordarem, e um espelho sem guard envelhece calado -- a
divergencia so aparece quando alguem julga um job com o numero errado.

POR QUE UM MECANISMO E NAO QUATRO. Antes desta entrega havia dois guards, um por
plataforma (`test_runtime_emr_matrix.py` para EMR on EC2 e
`test_emr_serverless_runtime_boundary.py` para o Serverless), cada um com o seu
proprio parser de markdown escrito a mao. Acrescentar EMR on EKS e Glue faria
quatro parsers para o mesmo formato de tabela -- quatro lugares para o mesmo bug
de parsing, e nenhum deles capaz de falhar quando o OUTRO parasse de ler a
pagina. O que muda de plataforma para plataforma nao e o mecanismo: e o
CABECALHO da tabela e o vocabulario de componentes. Entao o que varia vira dado
(`PLATAFORMAS`) e o mecanismo fica um so.

O QUE ELE COMPARA, e por que a comparacao e nos dois sentidos. Para cada
componente que a pagina publica EM TABELA:

  - celula na pagina e ausente no YAML  -> falha (o espelho perdeu um fato)
  - celula no YAML e ausente na pagina  -> falha (o motor afirma o que a pagina
                                            auditada nao diz)
  - as duas presentes                   -> tem que ser a MESMA string

Ausencia declarada dos dois lados nao e falha -- e o caso normal de `emr-6.4.0`
sem Iceberg, e a semantica que este motor da para "a fonte nao publica".

O QUE ELE NAO ALCANCA, declarado em vez de escondido: componente que o YAML
carrega e a pagina NAO publica em coluna de tabela nao entra na comparacao --
hoje isso e so `java` no YAML do Glue, cuja tabela da secao 1 nao tem coluna de
Java. Um guard que fingisse cobrir isso seria pior do que um que diz o que nao
cobre.

CONJUNTO DE RELEASES, e a assimetria que a pagina de EMR on EC2 ja media. Uma
release no YAML e ausente da pagina e SEMPRE falha: e o codigo afirmando o que o
documento nao diz. O sentido contrario depende do perfil de drift da fonte --
serie estavel (6.x, 5.x) nao ganha linha nova, entao linha so na pagina e falha;
serie com churn garantido (7.x, e as `spark-8*`) ganha um minor a cada 90 dias,
e exigir igualdade faria o guard falhar ~4x/ano por motivo que nao e drift do
que a matriz ja conhece. Ali sai `UserWarning`, como o guard de EC2 ja fazia.

A QUINTA ENTRADA NAO E UM RUNTIME, e ela cabe aqui sem mecanismo novo. A matriz
do Control-M Automation API (`knowledge/controlm/`) tem DOIS eixos e nao um --
capacidade com fronteira de versao, e componente com exigencia por versao --,
entao ela nao tem `versions:` e nao carrega por `_carrega_matriz_fechada` (a
razao mora em `sparkforge/controlm/__init__.py`). O que ela tem em comum com as
quatro e exatamente o que ESTE arquivo precisa: um `.md` com tabelas e um
`.yaml` que ninguem obriga a concordar com elas. `matrix.drift_view()` achata os
dois eixos e as recusas em `{chave: {coluna: valor}}`, que e a forma que o
mecanismo ja compara -- entao Control-M entra como uma entrada em `PLATAFORMAS`,
com tres tabelas e cinco colunas proprias, e nao como um quinto parser de
markdown para o mesmo formato de tabela.

E o `churn` dela e VAZIO de proposito, ao contrario da intuicao. A pagina da BMC
e `Monthly` e rola ~12x/ano -- mais churn que qualquer das quatro. Mas a FAIXA
que a matriz cobre (`9.0.21.200`-`9.0.22.100`) e passado FECHADO: nada que role
muda o que aconteceu no `9.0.21.300`. Linha nova na pagina cai fora da faixa e
nao entra na tabela; linha da faixa que mudar e errata da BMC, e tem de falhar
duro. Aqui `UserWarning` seria o alarme errado.
"""
from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from sparkforge.controlm import matrix as controlm_matrix
from sparkforge.facts import runtime_matrix

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"

# Grafias de "a fonte nao publica esta celula". Vem das quatro paginas, e cada
# uma escreve do seu jeito: travessao na de EC2, `nao publicado` na de EKS, `nao
# existe` na do Serverless, `a verificar` na do Glue. Todas significam a mesma
# coisa para este guard -- e nenhuma delas pode virar valor.
_AUSENTE = frozenset(
    {
        "",
        "-",
        "—",
        "nao publicado",
        "não publicado",
        "nao existe",
        "não existe",
        "a verificar",
    }
)


def _limpa(celula: str) -> str:
    """Tira a marcacao que a prosa usa para dar enfase e nao muda o dado.

    As paginas marcam a celula divergente com `**negrito**` e o release label
    com crases. Comparar sem tirar isso acusaria drift onde houve so edicao de
    redacao -- e um guard que acusa o que nao e drift e um guard ignorado.
    """
    return celula.strip().strip("*").strip("`").strip()


def _e_ausente(valor: str) -> bool:
    # `*(nao esta na EMR_MATRIX)*` e `*(fora)*` sao comentarios em italico numa
    # celula de comparacao, nao valores. Comecam com parentese depois da
    # limpeza da enfase.
    return valor.lower() in _AUSENTE or valor.startswith("(")


@dataclass(frozen=True)
class Tabela:
    """Uma tabela de markdown identificada pelo seu cabecalho exato.

    Identificar por cabecalho, e nao por numero de secao ou por prefixo de
    linha, e o que permite ao mesmo mecanismo ler as duas tabelas da pagina de
    EC2 (7.x e 6.x tem o MESMO cabecalho e sao lidas as duas) e as duas de
    formato diferente da do Serverless (secao 2 e secao 4), sem que nenhuma das
    tabelas de prosa das mesmas paginas entre por engano.
    """

    cabecalho: tuple[str, ...]
    chave: str
    colunas: Mapping[str, str]
    conjuntos: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Plataforma:
    nome: str
    doc: str
    yaml: str
    carrega: Callable[[], dict[str, dict[str, Any]]]
    tabelas: tuple[Tabela, ...]
    churn: tuple[str, ...] = ()
    minimo: int = 1
    componentes: frozenset[str] = field(default_factory=frozenset)

    @property
    def caminho_doc(self) -> Path:
        return KNOWLEDGE / self.doc

    @property
    def caminho_yaml(self) -> Path:
        return KNOWLEDGE / self.yaml


def _chave(rotulo: str) -> str:
    """Normaliza o rotulo de linha para a chave do YAML.

    Mesma normalizacao de `sparkforge.facts.runtime_detect._emr_key`: o prefixo
    `emr-` cai, o resto sobrevive cru -- inclusive `spark-8.0.0`, que e release
    label de verdade e nao um numero.
    """
    limpo = _limpa(rotulo)
    return limpo[4:] if limpo.lower().startswith("emr-") else limpo


def tabela_do_documento(plataforma: Plataforma) -> dict[str, dict[str, Any]]:
    """Le as tabelas declaradas da pagina `.md` e devolve a matriz que elas
    publicam, indexada como o YAML indexa.

    Parsear o markdown em vez de reescrever os valores no teste e o que faz
    deste um guard de DRIFT e nao de uma terceira copia da matriz para manter
    desatualizada.
    """
    linhas: dict[str, dict[str, Any]] = {}
    atual: Tabela | None = None
    indices: dict[str, int] = {}
    chave_idx = -1

    for linha in plataforma.caminho_doc.read_text(encoding="utf-8").splitlines():
        if not linha.startswith("|"):
            atual = None
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        cabecalho = tuple(celulas)
        casada = next((t for t in plataforma.tabelas if t.cabecalho == cabecalho), None)
        if casada is not None:
            atual = casada
            chave_idx = celulas.index(casada.chave)
            # `.index` pega a PRIMEIRA ocorrencia, e a pagina de EKS repete o
            # rotulo `bate` duas vezes -- nenhuma das duas e lida, entao a
            # repeticao nao ambigua nada que este guard use.
            indices = {c: celulas.index(rot) for c, rot in casada.colunas.items()}
            continue
        if atual is None:
            continue
        if set("".join(celulas)) <= {"-", ":"}:
            continue
        chave = _chave(celulas[chave_idx])
        # A linha so vira release DESTA matriz se publicar ao menos uma celula.
        # A tabela da secao 2 do Serverless lista as 30 releases da matriz de
        # EC2 para poder dizer `nao existe` em seis delas -- sao linhas sobre a
        # OUTRA plataforma, e conta-las como release do Serverless faria o guard
        # exigir do YAML uma linha que a fonte declara inexistente.
        destino: dict[str, Any] = {}
        for componente, idx in indices.items():
            valor = _limpa(celulas[idx])
            if _e_ausente(valor):
                continue
            if componente in atual.conjuntos:
                destino[componente] = tuple(
                    p.strip() for p in valor.split(",") if p.strip()
                )
            else:
                destino[componente] = valor
        if destino:
            linhas.setdefault(chave, {}).update(destino)
    return linhas


PLATAFORMAS: tuple[Plataforma, ...] = (
    Plataforma(
        nome="glue",
        doc="glue/runtime-matrix.md",
        yaml="glue/runtime-matrix.yaml",
        carrega=runtime_matrix.load,
        minimo=5,
        componentes=frozenset({"spark", "python", "scala", "iceberg"}),
        tabelas=(
            Tabela(
                cabecalho=(
                    "AWS Glue",
                    "Apache Spark",
                    "Python",
                    "Scala",
                    "Iceberg",
                    "Hudi",
                    "Delta Lake",
                ),
                chave="AWS Glue",
                colunas={
                    "spark": "Apache Spark",
                    "python": "Python",
                    "scala": "Scala",
                    "iceberg": "Iceberg",
                },
            ),
        ),
    ),
    Plataforma(
        nome="emr",
        doc="emr/runtime-matrix.md",
        yaml="emr/runtime-matrix.yaml",
        carrega=runtime_matrix.load_emr,
        churn=("7.",),
        minimo=30,
        componentes=frozenset(
            {"spark", "hadoop", "iceberg", "python_installed", "python"}
        ),
        tabelas=(
            Tabela(
                cabecalho=(
                    "Release",
                    "Spark",
                    "Hadoop",
                    "Iceberg",
                    "Python instalado",
                    "Python do PySpark",
                ),
                chave="Release",
                colunas={
                    "spark": "Spark",
                    "hadoop": "Hadoop",
                    "iceberg": "Iceberg",
                    "python_installed": "Python instalado",
                    "python": "Python do PySpark",
                },
                conjuntos=frozenset({"python_installed"}),
            ),
        ),
    ),
    Plataforma(
        nome="emr-serverless",
        doc="emr-serverless/runtime-matrix.md",
        yaml="emr-serverless/runtime-matrix.yaml",
        carrega=runtime_matrix.load_emr_serverless,
        minimo=26,
        componentes=frozenset({"spark", "iceberg"}),
        tabelas=(
            Tabela(
                cabecalho=(
                    "Release",
                    "Spark no EC2",
                    "Spark no Serverless",
                    "Comunidade bate",
                ),
                chave="Release",
                colunas={"spark": "Spark no Serverless"},
            ),
            Tabela(
                cabecalho=("Release label", "Spark", "Iceberg", "Observação"),
                chave="Release label",
                colunas={"spark": "Spark", "iceberg": "Iceberg"},
            ),
        ),
    ),
    Plataforma(
        nome="emr-eks",
        doc="emr-eks/runtime-matrix.md",
        yaml="emr-eks/runtime-matrix.yaml",
        carrega=runtime_matrix.load_emr_eks,
        churn=("7.", "spark-"),
        minimo=34,
        componentes=frozenset({"spark", "iceberg", "hudi", "delta"}),
        tabelas=(
            Tabela(
                cabecalho=(
                    "Release",
                    "Spark (EKS)",
                    "Spark (EC2)",
                    "bate",
                    "Iceberg (EKS)",
                    "Iceberg (EC2)",
                    "bate",
                ),
                chave="Release",
                colunas={"spark": "Spark (EKS)", "iceberg": "Iceberg (EKS)"},
            ),
            Tabela(
                cabecalho=("Release", "Hudi (EKS)", "Delta (EKS)"),
                chave="Release",
                colunas={"hudi": "Hudi (EKS)", "delta": "Delta (EKS)"},
            ),
        ),
    ),
    # Control-M Automation API -- dois eixos e as recusas, tres tabelas. Ver o
    # ultimo paragrafo do docstring deste modulo sobre por que ela cabe aqui e
    # por que o `churn` e vazio.
    Plataforma(
        nome="controlm",
        doc="controlm/automation-api-matrix.md",
        yaml="controlm/automation-api-matrix.yaml",
        carrega=controlm_matrix.drift_view,
        minimo=69,
        componentes=controlm_matrix.DRIFT_COLUMNS,
        tabelas=(
            Tabela(
                cabecalho=("Capacidade", "Fronteira", "Versão", "Substituída por"),
                chave="Capacidade",
                colunas={
                    "boundary": "Fronteira",
                    "at_version": "Versão",
                    "replaced_by": "Substituída por",
                },
            ),
            Tabela(
                cabecalho=("Componente", "Versão", "Exigência"),
                chave="Componente",
                colunas={"at_version": "Versão", "requirement": "Exigência"},
            ),
            Tabela(
                cabecalho=("Item", "Razão da recusa"),
                chave="Item",
                colunas={"unresolved_reason": "Razão da recusa"},
            ),
        ),
    ),
)

_POR_NOME = {p.nome: p for p in PLATAFORMAS}
_DOCUMENTOS = {p.nome: tabela_do_documento(p) for p in PLATAFORMAS}


def _casos_de_celula() -> list[tuple[str, str, str]]:
    """(plataforma, release, componente) para cada celula comparavel.

    Parametrizar por CELULA e nao por plataforma e o que faz a falha nomear a
    celula que divergiu, que e o unico jeito de o guard ser acionavel: "a matriz
    de EKS divergiu" nao diz onde olhar.
    """
    casos = []
    for plataforma in PLATAFORMAS:
        doc = _DOCUMENTOS[plataforma.nome]
        yaml = plataforma.carrega()
        for release in sorted(set(doc) & set(yaml)):
            for componente in sorted(plataforma.componentes):
                casos.append((plataforma.nome, release, componente))
    return casos


class TestAsPaginasForamParseadas:
    """Se o formato da tabela mudar, o parser devolve pouco ou nada e todo o
    resto deste arquivo passaria VAZIO -- guard que nao guarda."""

    @pytest.mark.parametrize("nome", sorted(_POR_NOME))
    def test_a_pagina_rendeu_o_numero_de_releases_esperado(self, nome):
        plataforma = _POR_NOME[nome]
        lidas = _DOCUMENTOS[nome]
        assert len(lidas) >= plataforma.minimo, (
            f"{plataforma.doc}: o parser leu {len(lidas)} releases e a pagina tem "
            f"ao menos {plataforma.minimo}. O formato da tabela mudou, e o guard "
            f"passaria vazio."
        )

    @pytest.mark.parametrize("nome", sorted(_POR_NOME))
    def test_toda_tabela_declarada_foi_encontrada(self, nome):
        plataforma = _POR_NOME[nome]
        texto = plataforma.caminho_doc.read_text(encoding="utf-8")
        cabecalhos = {
            tuple(c.strip() for c in linha.strip().strip("|").split("|"))
            for linha in texto.splitlines()
            if linha.startswith("|")
        }
        faltando = [t.cabecalho for t in plataforma.tabelas if t.cabecalho not in cabecalhos]
        assert not faltando, (
            f"{plataforma.doc}: o cabecalho {faltando} nao existe mais na pagina. "
            f"Sem ele a tabela inteira sai do guard em silencio."
        )


class TestOConjuntoDeReleases:
    @pytest.mark.parametrize("nome", sorted(_POR_NOME))
    def test_release_no_yaml_e_ausente_da_pagina_e_falha(self, nome):
        plataforma = _POR_NOME[nome]
        sobrando = sorted(set(plataforma.carrega()) - set(_DOCUMENTOS[nome]))
        assert not sobrando, (
            f"{plataforma.yaml} declara {sobrando} e {plataforma.doc} nao. "
            f"Este sentido E sempre falha: e o motor afirmando o que a pagina "
            f"auditada nao diz."
        )

    @pytest.mark.parametrize("nome", sorted(_POR_NOME))
    def test_release_so_na_pagina_falha_em_serie_estavel_e_avisa_em_serie_com_churn(
        self, nome
    ):
        plataforma = _POR_NOME[nome]
        faltando = sorted(set(_DOCUMENTOS[nome]) - set(plataforma.carrega()))
        churn = [r for r in faltando if r.startswith(plataforma.churn)] if plataforma.churn else []
        estaveis = [r for r in faltando if r not in churn]
        assert not estaveis, (
            f"{plataforma.doc} publica {estaveis} e {plataforma.yaml} nao. "
            f"A serie e estavel -- ela nao ganha linha nova --, entao isto e "
            f"drift, nao atraso."
        )
        if churn:
            warnings.warn(
                f"{plataforma.yaml} desatualizada: a pagina ja tem {churn}. "
                f"Considere acrescentar. Isto NAO e drift do que a matriz conhece.",
                UserWarning,
                stacklevel=1,
            )


class TestCadaCelula:
    @pytest.mark.parametrize(
        "nome,release,componente",
        _casos_de_celula(),
        ids=lambda v: str(v),
    )
    def test_a_celula_do_yaml_e_a_da_pagina_dizem_a_mesma_coisa(
        self, nome, release, componente
    ):
        plataforma = _POR_NOME[nome]
        na_pagina = _DOCUMENTOS[nome][release].get(componente)
        no_yaml = plataforma.carrega()[release].get(componente)
        assert no_yaml == na_pagina, (
            f"{nome} {release}.{componente}: {plataforma.yaml} diz {no_yaml!r} e "
            f"{plataforma.doc} diz {na_pagina!r}. Celula que a fonte nao publica "
            f"fica AUSENTE dos dois lados; valor diferente e drift do espelho."
        )
