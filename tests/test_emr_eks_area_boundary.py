"""A fronteira entre as TRES areas de EMR, medida nos seis pares.

`tests/test_rules_emrs_boundary.py` mede a fronteira entre `SF-EMR` (EC2) e
`SF-EMRS` (Serverless) -- duas plataformas, duas direcoes. Com a terceira
(`SF-EMRK`, EMR on EKS) as direcoes viram **seis**, e o par novo e o que mais
importa: uma regra de EC2 ou de Serverless disparando sobre `describe-job-run`
de EKS produziria um achado com vocabulario de outra plataforma -- grupo de
instancia, purchasing option, capacidade pre-inicializada, janela de auto-stop --
sobre uma configuracao que talvez esteja correta. Nenhuma dessas coisas existe
no modelo de execucao do `emr-containers`.

Este arquivo generaliza o molde de duas plataformas em vez de copia-lo: a area,
o namespace, o corpus e o golden de facts de cada plataforma vivem numa tabela
so (`PLATAFORMAS`), e cada afirmacao e parametrizada sobre ela. Acrescentar uma
quarta plataforma e acrescentar uma linha.

**As tres armadilhas que decidem se este arquivo mede alguma coisa.**

1. `SF-EMR-` e prefixo de `SF-EMRS-` E de `SF-EMRK-`. Classificar por
   `startswith("SF-EMR")` faz as duas areas novas contarem como EC2, e entao as
   direcoes que saem de `SF-EMR` passariam por engano, provando o contrario do
   que prometem. Aqui a area vem do DOCUMENTO do catalogo, e
   `TestComoAAreaEComparada` trava a equivalencia com o id por igualdade exata.

2. Verde por skip. `judge` nao avalia regra fora de `runtime_scope`, e regra nao
   avaliada nao dispara. Por isso cada direcao julga com o `runtime` declarado
   no `meta.yaml` da propria fixture -- que difere entre os tres corpora -- e
   afirma sobre a lista de `skipped` que o silencio da area vizinha veio de
   `requires_facts`, nunca de escopo ou bloqueio.

3. Verde sobre corpus mudo. Zero achado dos tres lados satisfaz "nenhum achado
   da area vizinha". `TestOsTresCorporaEstaoVivos` exige que cada corpus dispare
   TODAS as regras da sua propria area antes de qualquer afirmacao sobre as de
   fora -- e por isso a fronteira vale tambem quando ha achado, e nao so nas
   fixtures saudaveis.

A fronteira e **por construcao, nao por supressao**: cada area julga os facts do
seu proprio extrator, e por isso nenhuma precisa ser calada. A construcao tem
nome nas tres decisoes de namespace -- `emr.`, `emrs.` (D-5d-1) e `emrc.` (D-2
da spec de EMR on EKS) --, escolhidas para que nenhum seja prefixo do outro.

Os facts vem dos GOLDENS commitados (`expected/facts.json`), carregados pela
mesma porta que a CLI usa em `sparkforge judge --facts` (`_facts_from_dicts`).
Reextrair aqui mediria o extrator de novo -- coisa que os `test_fixtures_golden_*`
ja fazem -- e faria este arquivo depender de tres extratores para afirmar sobre
regras.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters._core import AdapterError, _facts_from_dicts, judge_findings
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import ROUTING_FILE, catalog_dir, load_catalog

ROOT = Path(__file__).resolve().parents[1]

EC2 = "SF-EMR"
SERVERLESS = "SF-EMRS"
EKS = "SF-EMRK"


@dataclass(frozen=True)
class Plataforma:
    area: str
    namespace: str
    corpus: Path
    artefato: str


# O namespace de fact de cada area. Ler o do vizinho e a unica forma de uma
# regra falar do artefato errado, e e por isso que estes pares tem teste proprio.
PLATAFORMAS: dict[str, Plataforma] = {
    EC2: Plataforma(EC2, "emr.", ROOT / "fixtures" / "emr", "describe-cluster"),
    SERVERLESS: Plataforma(
        SERVERLESS, "emrs.", ROOT / "fixtures" / "emr_serverless", "get-application"
    ),
    EKS: Plataforma(EKS, "emrc.", ROOT / "fixtures" / "emr_eks", "describe-job-run"),
}

AREAS = sorted(PLATAFORMAS)

# Os seis pares ORDENADOS. `(alvo, vizinha)` le-se "nenhuma regra de `vizinha`
# dispara sobre o corpus de `alvo`". Sao seis e nao tres porque a direcao
# importa: regra de EC2 sobre artefato de EKS e um defeito diferente de regra de
# EKS sobre artefato de EC2, e so um dos dois seria pego por um teste simetrico.
PARES = [(a, b) for a in AREAS for b in AREAS if a != b]


# ---------------------------------------------------------------------------
# Area: lida do documento, porque a regra carregada nao a carrega.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _area_por_arquivo() -> dict[str, str]:
    """`nome do .yaml` -> `area:` declarada no cabecalho do documento.

    O `load_catalog` propaga `catalog_version` e `_source_file` para dentro de
    cada regra, mas NAO o `area:` do cabecalho. Entao ler a area declarada exige
    abrir o documento, e `_source_file` e a ponte entre as duas leituras.
    """
    base = catalog_dir()
    mapa: dict[str, str] = {}
    for path in sorted(base.glob("*.yaml")):
        if path.name == ROUTING_FILE:
            continue
        documento = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
        area = documento.get("area")
        if area:
            mapa[path.name] = str(area)
    return mapa


def _area_declarada(regra: dict) -> str | None:
    return _area_por_arquivo().get(regra.get("_source_file", ""))


def _area_do_id(rule_id: str) -> str:
    """`rsplit` e igualdade exata, nunca `startswith`.

    `SF-EMRS-001` devolve `SF-EMRS` e `SF-EMRK-001` devolve `SF-EMRK`, os dois
    diferentes de `SF-EMR` -- e essa diferenca e o arquivo inteiro.
    """
    return rule_id.rsplit("-", 1)[0]


def _kinds_lidos(regra: dict) -> set[str]:
    """Todo kind que a regra le: `requires_facts` mais `fact:`/`absent:`."""
    return set(regra.get("requires_facts") or []) | _kinds_in_when(regra.get("when"))


def _kinds_in_when(no: object) -> set[str]:
    achados: set[str] = set()
    if isinstance(no, dict):
        for chave, valor in no.items():
            if chave in {"fact", "absent"} and isinstance(valor, str):
                achados.add(valor)
            else:
                achados |= _kinds_in_when(valor)
    elif isinstance(no, list):
        for item in no:
            achados |= _kinds_in_when(item)
    return achados


def _regras_da_area(catalogo: list[dict], area: str) -> list[dict]:
    """As regras de uma area, pela area DECLARADA, com o id como confirmacao.

    As duas leituras precisam concordar -- `test_area_do_documento_e_area_do_id`
    reprova antes deste ponto se nao concordarem. Exigir as duas aqui torna o
    recorte robusto ao caso que motiva o arquivo inteiro: uma regra nova entrando
    no arquivo errado nao entra silenciosamente na contagem de nenhum dos lados.
    """
    return [
        r for r in catalogo if _area_declarada(r) == area and _area_do_id(r["id"]) == area
    ]


# ---------------------------------------------------------------------------
# Os tres corpora, julgados pela mesma porta por onde o produto julga.
# ---------------------------------------------------------------------------


def _dirs(raiz: Path) -> list[Path]:
    return sorted(p for p in raiz.iterdir() if p.is_dir())


@lru_cache(maxsize=1)
def _catalogo() -> tuple[dict, ...]:
    """O catalogo inteiro, uma vez. `judge` recebe TODAS as regras de proposito:
    a fronteira e sobre o que o produto faz, e o produto nunca filtra o catalogo
    por area antes de julgar."""
    return tuple(load_catalog())


def _julgar(directory: Path) -> dict:
    """Um golden commitado, julgado com o runtime declarado pela propria fixture.

    `_facts_from_dicts` e a mesma funcao que `sparkforge judge --facts` chama:
    afirmar sobre outra porta mediria um caminho que nenhum operador percorre.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    payload = json.loads(
        (directory / "expected" / "facts.json").read_text(encoding="utf-8")
    )
    facts = _facts_from_dicts(payload)
    findings, skipped = judge(facts, _catalogo(), meta["runtime"], return_skipped=True)
    return {
        "nome": directory.name,
        "runtime": meta["runtime"],
        "facts": facts,
        "findings": findings,
        "skipped": skipped,
    }


@cache
def _corpus_julgado(area: str) -> tuple[dict, ...]:
    return tuple(_julgar(d) for d in _dirs(PLATAFORMAS[area].corpus))


@pytest.fixture(scope="module")
def catalogo() -> list[dict]:
    return list(_catalogo())


@pytest.fixture(scope="module")
def corpus():
    return _corpus_julgado


class TestComoAAreaEComparada:
    """O mecanismo, antes da medida -- porque comparar errado passa por engano."""

    def test_o_loader_nao_propaga_a_area_para_dentro_da_regra(self, catalogo):
        """A razao de `_area_por_arquivo` existir, escrita como medida.

        Se um dia o `load_catalog` passar a propagar `area` como propaga
        `catalog_version` e `_source_file`, este teste reprova e o recado e:
        apague `_area_por_arquivo` e leia `regra["area"]`.
        """
        com_area = sorted(r["id"] for r in catalogo if "area" in r)
        assert not com_area, (
            f"{com_area} chegam do loader ja com `area`. O mecanismo deste arquivo "
            f"-- ler o documento e casar por `_source_file` -- deixou de ser "
            f"necessario."
        )

    @pytest.mark.parametrize("area", AREAS)
    def test_a_area_existe_no_catalogo(self, catalogo, area):
        assert _regras_da_area(catalogo, area), (
            f"nenhuma regra na area {area}. Uma tabela `PLATAFORMAS` que nomeia "
            f"area sem regra faria todos os pares que saem dela passarem por "
            f"vacuidade."
        )

    def test_area_do_documento_e_area_do_id_concordam(self, catalogo):
        """A guarda contra regra nova no arquivo errado.

        Uma `SF-EMRK-005` escrita dentro de `emr-infra.yaml` herdaria a area
        `SF-EMR` do documento e sairia do recorte de `SF-EMRK` sem que ninguem
        notasse -- a fronteira continuaria verde sobre uma regra que ela nunca
        olhou.
        """
        mapa = _area_por_arquivo()
        divergentes = sorted(
            (r["id"], r["_source_file"], mapa.get(r["_source_file"]))
            for r in catalogo
            if mapa.get(r["_source_file"]) != _area_do_id(r["id"])
        )
        assert not divergentes, (
            f"regra em documento de outra area: {divergentes}. O id e o cabecalho "
            f"precisam dizer a mesma coisa, senao a area de uma regra depende de "
            f"qual das duas leituras o teste escolheu."
        )

    def test_prefixo_de_id_nao_discrimina_as_tres_areas(self, catalogo):
        """A armadilha, provada em vez de comentada, agora com DUAS vitimas.

        `startswith("SF-EMR")` classifica toda regra Serverless E toda regra de
        EKS como EC2. O teste existe para que, se alguem trocar a comparacao
        exata por prefixo, exista um lugar que ja disse por que aquilo nao
        funciona.
        """
        for area in (SERVERLESS, EKS):
            ids = [r["id"] for r in _regras_da_area(catalogo, area)]
            assert ids, f"nenhuma regra {area} no catalogo: nao ha o que comparar"
            assert all(rid.startswith(EC2) for rid in ids), (
                f"esperava que todo id {area} casasse `startswith('{EC2}')`. Se isso "
                f"deixou de valer, a armadilha mudou de forma e este arquivo precisa "
                f"ser relido, nao so ajustado."
            )
            assert all(_area_do_id(rid) != EC2 for rid in ids), (
                f"a comparacao exata deixou de separar {area} de {EC2} -- que e a "
                f"unica coisa que impede este arquivo de provar o oposto do que "
                f"promete."
            )


class TestNenhumaAreaLeONamespaceDaVizinha:
    """A fronteira no CATALOGO, antes de qualquer fixture.

    Os tres prefixos sao disjuntos porque o ponto esta no lugar certo: `emrs.` e
    `emrc.` nao comecam com `emr.`, e nenhum dos dois comeca com o outro. Foi por
    isso que a Task 2 da 5d escolheu `emrs.` em vez de `emr.serverless.`, e a
    D-2 desta fase escolheu `emrc.` em vez de `emr.eks.`.
    """

    @pytest.mark.parametrize("alvo,vizinha", PARES)
    def test_os_namespaces_sao_disjuntos_por_prefixo(self, alvo, vizinha):
        assert not PLATAFORMAS[alvo].namespace.startswith(PLATAFORMAS[vizinha].namespace)

    @pytest.mark.parametrize("alvo,vizinha", PARES)
    def test_nenhuma_regra_le_kind_da_area_vizinha(self, catalogo, alvo, vizinha):
        alheio = PLATAFORMAS[vizinha].namespace
        for regra in _regras_da_area(catalogo, alvo):
            invasores = sorted(k for k in _kinds_lidos(regra) if k.startswith(alheio))
            assert not invasores, (
                f"{regra['id']} le {invasores}, do namespace de {vizinha}. Cada area "
                f"julga os facts do seu proprio extrator: `{PLATAFORMAS[alvo].artefato}` "
                f"e `{PLATAFORMAS[vizinha].artefato}` descrevem modelos de execucao "
                f"diferentes, e regra que le os dois produz achado que cita evidencia "
                f"de outra coisa."
            )

    @pytest.mark.parametrize("area", AREAS)
    def test_toda_regra_exige_ao_menos_um_kind_do_proprio_namespace(self, catalogo, area):
        """O que faz a fronteira ser por CONSTRUCAO e nao por sorte.

        `judge` pula regra cujo `requires_facts` nao esta presente. Se uma regra
        de qualquer das tres areas nao exigir nenhum kind do seu namespace, ela
        seria AVALIADA sobre o artefato do vizinho, e o silencio passaria a
        depender do `when` -- que e onde erro de regra mora.
        """
        proprio = PLATAFORMAS[area].namespace
        for regra in _regras_da_area(catalogo, area):
            exigidos = set(regra.get("requires_facts") or [])
            assert any(k.startswith(proprio) for k in exigidos), (
                f"{regra['id']} nao exige nenhum kind `{proprio}*` em "
                f"`requires_facts` (exige {sorted(exigidos)}). Sem isso a regra "
                f"chega a ser avaliada sobre o artefato de outro modelo de "
                f"execucao, e a fronteira deixa de ser por construcao."
            )


class TestOsTresCorporaEstaoVivos:
    """Sem isto, os seis pares passariam com extracao quebrada.

    Zero achado dos tres lados satisfaz "nenhum achado da area vizinha" -- e
    seria verde sobre nada. Exigir que TODA regra da area dispare em ALGUMA
    fixture do proprio corpus e o que faz a fronteira valer tambem quando ha
    achado, e nao so nas fixtures saudaveis.
    """

    @pytest.mark.parametrize("area", AREAS)
    def test_o_corpus_dispara_a_propria_area(self, catalogo, corpus, area):
        julgados = corpus(area)
        disparadas = {f.rule_id for j in julgados for f in j["findings"]}
        esperadas = {r["id"] for r in _regras_da_area(catalogo, area)}
        assert esperadas <= disparadas, (
            f"regras {sorted(esperadas - disparadas)} nao dispararam em nenhuma "
            f"fixture de `{PLATAFORMAS[area].corpus.name}`. A fronteira medida sobre "
            f"um corpus mudo nao mede nada."
        )

    @pytest.mark.parametrize("area", AREAS)
    def test_o_corpus_tem_fixture_saudavel_e_fixture_com_achado(self, corpus, area):
        """A fronteira precisa valer nos dois regimes, e este teste prova que o
        corpus tem os dois. Um corpus so de fixtures saudaveis mediria a
        fronteira apenas onde nenhuma regra chega a produzir texto."""
        julgados = corpus(area)
        com_achado = [j["nome"] for j in julgados if j["findings"]]
        sem_achado = [j["nome"] for j in julgados if not j["findings"]]
        assert com_achado, f"`{PLATAFORMAS[area].corpus.name}` nao tem fixture com achado"
        assert sem_achado, f"`{PLATAFORMAS[area].corpus.name}` nao tem fixture saudavel"


class TestFronteiraEntreAsTresAreas:
    """Os seis pares. O trio novo -- toda direcao que toca `SF-EMRK` -- e o que
    esta fase acrescenta; os dois antigos continuam medidos aqui pela mesma
    tabela, e nao ha razao para eles divergirem de
    `tests/test_rules_emrs_boundary.py`."""

    @pytest.mark.parametrize("alvo,vizinha", PARES)
    def test_nenhuma_regra_da_vizinha_dispara_sobre_o_corpus(
        self, catalogo, corpus, alvo, vizinha
    ):
        julgados = corpus(alvo)
        assert julgados, f"corpus de {alvo} vazio"
        vetadas = {r["id"] for r in _regras_da_area(catalogo, vizinha)}
        invasoes = sorted(
            (j["nome"], f.rule_id, tuple(f.evidence))
            for j in julgados
            for f in j["findings"]
            if f.rule_id in vetadas
        )
        assert not invasoes, (
            f"regra de {vizinha} disparou sobre `{PLATAFORMAS[alvo].artefato}`: "
            f"{invasoes}. O achado cobraria do operador uma configuracao que a API "
            f"do modelo de execucao dele nao aceita, citando evidencia de "
            f"`{PLATAFORMAS[vizinha].artefato}`."
        )


class TestOSilencioNaoEPorEscopo:
    """O verde pior que vermelho, fechado nos seis pares.

    `judge` pula por tres motivos, e so um deles e a fronteira. `runtime_scope` e
    `blocked_on` calam a regra ANTES de olhar para os facts -- se fosse por eles,
    os seis testes acima passariam sem que a regra vizinha tivesse chegado perto
    do artefato. `requires_facts` e o motivo legitimo, e e a fronteira por
    construcao acontecendo.

    O par que corre mais risco e `(EKS, EC2)`: as fixtures de `fixtures/emr_eks/`
    declaram `runtime: {spark: "3.5.2-amzn-1"}`, e uma regra de EC2 com
    `runtime_scope` sobre `emr` sairia calada por escopo em vez de por falta de
    fact -- verde hoje, vermelho no dia em que o escopo mudasse, longe daqui.
    """

    @pytest.mark.parametrize("alvo,vizinha", PARES)
    def test_a_area_vizinha_nunca_e_pulada_por_escopo_ou_bloqueio(
        self, catalogo, corpus, alvo, vizinha
    ):
        regras = {r["id"] for r in _regras_da_area(catalogo, vizinha)}
        culpados = sorted(
            (j["nome"], str(j["runtime"]), s["rule_id"], s["reason"])
            for j in corpus(alvo)
            for s in j["skipped"]
            if s["rule_id"] in regras and s["reason"] in {"runtime_scope", "blocked_on"}
        )
        assert not culpados, (
            f"regra de {vizinha} calada por `{{runtime_scope, blocked_on}}` sobre o "
            f"artefato de {alvo}: {culpados}. A fronteira ficaria verde sem nunca "
            f"ter sido avaliada."
        )

    @pytest.mark.parametrize("alvo,vizinha", PARES)
    def test_toda_regra_vizinha_e_calada_por_falta_de_fact(
        self, catalogo, corpus, alvo, vizinha
    ):
        """A afirmacao positiva: nao e que a regra nao disparou, e que ela foi
        alcancada e nao teve com que se sustentar. Toda regra da area vizinha,
        em toda fixture, aparece em `skipped` com `reason: requires_facts`."""
        regras = {r["id"] for r in _regras_da_area(catalogo, vizinha)}
        for j in corpus(alvo):
            por_falta = {
                s["rule_id"] for s in j["skipped"] if s["reason"] == "requires_facts"
            }
            faltando = sorted(regras - por_falta)
            # So os skips da area vizinha na mensagem: despejar os skips
            # legitimos das outras areas esconde a linha que importa.
            visto = [s for s in j["skipped"] if s["rule_id"] in regras]
            assert not faltando, (
                f"em `{j['nome']}`, as regras {faltando} da area {vizinha} nao foram "
                f"puladas por `requires_facts`. Ou elas foram avaliadas sobre o "
                f"artefato de {alvo}, ou foram caladas por outro motivo. Skips de "
                f"{vizinha} nesta fixture: {visto}"
            )


# ---------------------------------------------------------------------------
# A outra fronteira: a MATRIZ de EC2 invadindo o eixo de runtime do EKS.
# ---------------------------------------------------------------------------

# O golden de `emrc.*` sobre o qual o contrafactual e medido. Qualquer um serve
# -- nenhum deles carrega um unico fact de EC2 --, e este e o saudavel, para que
# a afirmacao seja sobre o runtime e nunca sobre um achado.
FACTS_EKS = PLATAFORMAS[EKS].corpus / "job_run_saudavel" / "expected" / "facts.json"

# Os tres eixos que a `EMR_MATRIX` de EMR on EC2 deriva de um release label. A
# DV-1 mediu que a matriz de EKS existe e DIVERGE da de EC2 em celulas reais --
# Iceberg em 6 de 26 releases comparaveis, Spark em 4 --, e que Python nao e
# publicado por familia em lugar nenhum do EKS (2 de 34 paginas, em prosa).
EIXOS_DERIVADOS = ("spark", "python", "iceberg")

# Tres releases que a DV-1 nomeia como divergentes, com o que a matriz de EKS
# publica de fato (`knowledge/emr-eks/runtime-matrix.md` §2).
RELEASES_DIVERGENTES = [
    # (release, eixo, valor do EC2 que a EMR_MATRIX derivaria, o que o EKS publica)
    ("6.5.0", "iceberg", "0.12.0", "nao publicado"),
    ("7.7.0", "iceberg", "1.7.1-amzn-0", "1.6.1-amzn-2"),
    ("7.7.0", "spark", "3.5.3-amzn-1", "3.5.3-amzn-0"),
]


def _judge_com_emr(release: str, facts_path: Path = FACTS_EKS) -> dict:
    return judge_findings(facts_path=str(facts_path), emr=release)


class TestOEixoDeRuntimeNaoVemDaMatrizDeEC2:
    """O contrafactual da divida que o `STATUS.md` registra para o Serverless.

    O `STATUS.md` registra que `sparkforge judge --facts <facts de EMR
    Serverless> --emr 7.5.0` grava `spark`, `python` e `iceberg` derivados da
    `EMR_MATRIX` -- que e de EMR on EC2 -- sobre um conjunto de facts que nao tem
    um unico fact de EC2. Tres campos inventados.

    Para EMR on EKS isso e PIOR, e a DV-1 mediu por que: no Serverless a AWS nao
    publica matriz, entao a de EC2 e inaplicavel por falta de fonte. No EKS a
    matriz EXISTE e diverge em celulas reais. A `EMR_MATRIX` de EC2 nao e
    inaplicavel aqui: ela e MEDIDAMENTE ERRADA.

    Estes testes provam que a terceira plataforma nao repete o erro: passar
    `--emr` junto de facts `emrc.*` nao pode encher eixo que a matriz de EKS nao
    sustenta.
    """

    def test_os_facts_do_contrafactual_sao_so_de_eks(self):
        """A premissa, medida antes da afirmacao. Se um fact `emr.*` de EC2
        entrasse neste golden, `--emr` passaria a ser uma declaracao legitima
        sobre o artefato presente, e os testes abaixo mediriam outra coisa."""
        payload = json.loads(FACTS_EKS.read_text(encoding="utf-8"))
        kinds = sorted({f["kind"] for f in payload})
        assert kinds, f"{FACTS_EKS} vazio"
        assert all(k.startswith("emrc.") for k in kinds), (
            f"{FACTS_EKS} carrega kinds fora de `emrc.`: {kinds}"
        )

    @pytest.mark.parametrize("release,eixo,valor_ec2,no_eks", RELEASES_DIVERGENTES)
    def test_nao_grava_o_valor_de_ec2_num_eixo_que_o_eks_publica_diferente(
        self, release, eixo, valor_ec2, no_eks
    ):
        with pytest.raises(AdapterError) as erro:
            resultado = _judge_com_emr(release)
            pytest.fail(
                f"`--emr {release}` sobre facts `emrc.*` foi aceito e gravou "
                f"{eixo}={resultado['runtime'].get(eixo)!r} -- a `EMR_MATRIX` de EMR "
                f"on EC2 publica {valor_ec2!r} para essa release. A matriz de EMR on "
                f"EKS publica {no_eks!r} (`knowledge/emr-eks/runtime-matrix.md` §2, "
                f"DV-1). Nao e imprecisao: e um eixo de runtime inventado, e regra "
                f"versionada julgada sobre ele decide por uma versao que nunca rodou."
            )
        assert "EMR on EKS" in str(erro.value), (
            f"a recusa precisa NOMEAR a plataforma do conjunto de facts. Saiu: "
            f"{erro.value}"
        )

    @pytest.mark.parametrize("eixo", EIXOS_DERIVADOS)
    def test_nenhum_eixo_derivado_e_preenchido_a_partir_do_release_de_ec2(self, eixo):
        """A afirmacao geral, e nao so nas tres celulas divergentes.

        Acertar por coincidencia numa release onde as duas matrizes concordam
        nao e sustentacao: o valor continua vindo da tabela errada. `emr-7.5.0` e
        exatamente esse caso -- Spark concorda --, e por isso ele e o release
        medido aqui.
        """
        with pytest.raises(AdapterError) as erro:
            resultado = _judge_com_emr("7.5.0")
            pytest.fail(
                f"`--emr 7.5.0` sobre facts `emrc.*` foi aceito e gravou "
                f"{eixo}={resultado['runtime'].get(eixo)!r}, derivado da `EMR_MATRIX` "
                f"de EMR on EC2. Nenhuma fonte deste conjunto de facts sustenta esse "
                f"eixo: a DV-14 mediu que NADA alimenta `RuntimeContext.spark` a "
                f"partir de um fact `emrc.*`, e a DV-2 proibe derivar `iceberg` do "
                f"release label de EKS. Valor sem fonte e pior que lacuna declarada."
            )
        assert erro.value.exit_code == 2

    def test_sem_a_flag_o_julgamento_continua_acontecendo(self):
        """A recusa e da FLAG, nunca do artefato.

        Sem esta medida, fazer a guarda recusar o conjunto inteiro passaria
        igual: os testes acima so exigem que `--emr` nao seja aceito. O que o
        operador precisa e que o mesmo golden, sem a flag, continue sendo
        julgado -- as regras `SF-EMRK` sao `runtime_scope: {}` (DV-14) e nao
        precisam de eixo nenhum.
        """
        resultado = judge_findings(facts_path=str(FACTS_EKS))
        assert not resultado["runtime"]["emr"]
        assert resultado["total_count"] == 0, (
            f"`job_run_saudavel` e o negativo da area: nenhuma regra deve disparar. "
            f"Saiu {resultado['items']}"
        )

    def test_um_conjunto_com_os_dois_artefatos_continua_aceitando_a_flag(self, tmp_path):
        """A recusa e ESTREITA, e este e o contrafactual dela.

        Fundir um `describe-cluster` com um `describe-job-run` e caso legitimo, e
        ali `--emr` declara o lado de EC2 que esta de fato presente. Recusar
        tambem esse conjunto trocaria um valor inventado por uma porta fechada
        sobre artefato valido -- e ninguem descobriria antes de precisar dele.
        """
        eks = json.loads(FACTS_EKS.read_text(encoding="utf-8"))
        ec2_dir = PLATAFORMAS[EC2].corpus
        ec2_facts = json.loads(
            (sorted(_dirs(ec2_dir))[0] / "expected" / "facts.json").read_text(
                encoding="utf-8"
            )
        )
        assert any(f["kind"].startswith("emr.") for f in ec2_facts), (
            "o corpus de EC2 mudou de namespace e este contrafactual perdeu o sentido"
        )
        misto = tmp_path / "facts.json"
        misto.write_text(json.dumps(eks + ec2_facts), encoding="utf-8")
        # Nao ha `pytest.raises` aqui: a afirmacao E que a chamada volta. Qual
        # valor vence o eixo `emr` nao e assunto desta guarda -- a flag e
        # DECLARACAO e perde para o dump de `describe-cluster`, que e o que
        # `_EMR_FLAG_HELP` documenta e o que este conjunto tambem carrega.
        runtime = _judge_com_emr("7.5.0", misto)["runtime"]
        assert runtime["emr"], (
            "com um `describe-cluster` presente, o eixo `emr` tem fonte e nao pode "
            "sair vazio"
        )
