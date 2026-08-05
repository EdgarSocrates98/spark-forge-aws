"""A fronteira entre SF-EMR (EC2) e SF-EMRS (Serverless), medida.

As duas areas leem definicao de infraestrutura EMR. Se uma disparar sobre o
artefato da outra, o achado cita um fact que descreve outra coisa: um alerta de
Spot no TASK sobre uma application que nao tem grupo de instancia nenhum, ou uma
cobranca de capacidade pre-inicializada sobre um cluster que nunca teve
`initialCapacity`. E a §10.5 do spec da Fase 5d.

**Duas armadilhas decidem se este arquivo mede alguma coisa.**

1. `SF-EMR-` e prefixo de `SF-EMRS-`. Classificar por `startswith("SF-EMR")`
   faz `SF-EMRS-001` contar como area `SF-EMR` -- e entao
   `test_nenhuma_regra_emrs_dispara_sobre_ec2` passaria por engano, provando o
   contrario do que promete. Aqui a area vem do DOCUMENTO do catalogo, e
   `TestComoAAreaEComparada` trava a equivalencia com o id por igualdade exata.

2. Verde por skip. `judge` nao avalia regra fora de `runtime_scope`, e regra nao
   avaliada nao dispara -- o que faria os dois testes de fronteira passarem sem
   nunca terem olhado para a regra. Por isso cada direcao julga com o `runtime`
   declarado no `meta.yaml` da propria fixture (que difere entre os dois corpora:
   `{}` no Serverless por D-5d-5, versao real no EC2) e afirma sobre a lista de
   `skipped` que o silencio da area vizinha veio de `requires_facts`, nunca de
   escopo.

O precedente e `tests/test_dq_investigation_end_to_end.py`: a fronteira entre
duas areas e **por construcao, nao por supressao** -- cada area julga os facts do
seu proprio extrator, e por isso nenhuma precisa ser calada. Aqui a construcao
tem nome: a Task 2 escolheu o namespace `emrs.` justamente para que `emr.` nao
fosse prefixo dele (D-5d-1).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.emr_cluster import extract_emr_cluster_path
from sparkforge.facts.emr_serverless import extract_emr_serverless_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import ROUTING_FILE, catalog_dir, load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_EC2 = ROOT / "fixtures" / "emr"
FIXTURES_SERVERLESS = ROOT / "fixtures" / "emr_serverless"

EC2 = "SF-EMR"
SERVERLESS = "SF-EMRS"

# O namespace de fact de cada area. Ler o do vizinho e a unica forma de uma
# regra falar do artefato errado, e e por isso que este par tem teste proprio.
NAMESPACE = {EC2: "emr.", SERVERLESS: "emrs."}


# ---------------------------------------------------------------------------
# Area: lida do documento, porque a regra carregada nao a carrega.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _area_por_arquivo() -> dict[str, str]:
    """`nome do .yaml` -> `area:` declarada no cabecalho do documento.

    O `load_catalog` propaga `catalog_version` e `_source_file` para dentro de
    cada regra, mas NAO o `area:` do cabecalho -- medido na Task 5. Entao ler a
    area declarada exige abrir o documento, e `_source_file` e a ponte entre as
    duas leituras.
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
    """Mesma forma de `tests/test_dq_investigation_end_to_end.py:_area`.

    `rsplit` e igualdade exata, nao `startswith`: `SF-EMRS-001` devolve
    `SF-EMRS`, que e diferente de `SF-EMR` -- e essa diferenca e o arquivo
    inteiro.
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

    As duas leituras precisam concordar -- e `test_area_do_documento_e_area_do_id`
    reprova antes deste ponto se nao concordarem. Exigir as duas aqui torna o
    recorte robusto ao caso que motiva o teste inteiro: uma regra nova entrando
    no arquivo errado nao entra silenciosamente na contagem de nenhum dos lados.
    """
    return [
        r for r in catalogo if _area_declarada(r) == area and _area_do_id(r["id"]) == area
    ]


# ---------------------------------------------------------------------------
# Os dois corpora, julgados pela mesma porta por onde o produto julga.
# ---------------------------------------------------------------------------


def _dirs(raiz: Path) -> list[Path]:
    return sorted(p for p in raiz.iterdir() if p.is_dir())


@lru_cache(maxsize=1)
def _catalogo() -> tuple[dict, ...]:
    """O catalogo inteiro, uma vez. `judge` recebe TODAS as 77 regras de
    proposito: a fronteira e sobre o que o produto faz, e o produto nunca filtra
    o catalogo por area antes de julgar."""
    return tuple(load_catalog())


def _julgar(directory: Path, extrair) -> dict:
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extrair(directory)
    findings, skipped = judge(facts, _catalogo(), meta["runtime"], return_skipped=True)
    return {
        "nome": directory.name,
        "runtime": meta["runtime"],
        "facts": facts,
        "findings": findings,
        "skipped": skipped,
    }


def _extrair_ec2(directory: Path) -> list:
    """Mesma porta de `tests/test_fixtures_golden_emr.py`: laco sobre `*.json`."""
    input_dir = directory / "input"
    facts: list = []
    for dump in sorted(input_dir.glob("*.json")):
        facts.extend(extract_emr_cluster_path(dump, repo_root=input_dir))
    return facts


def _extrair_serverless(directory: Path) -> list:
    """Mesma porta de `tests/test_fixtures_golden_emr_serverless.py`: a funcao de
    arvore, que e o que `adapters/_core.py` chama quando o `--path` e diretorio."""
    input_dir = directory / "input"
    return extract_emr_serverless_tree(input_dir, repo_root=input_dir)


@pytest.fixture(scope="module")
def catalogo() -> list[dict]:
    return list(_catalogo())


@pytest.fixture(scope="module")
def sobre_serverless() -> list[dict]:
    return [_julgar(d, _extrair_serverless) for d in _dirs(FIXTURES_SERVERLESS)]


@pytest.fixture(scope="module")
def sobre_ec2() -> list[dict]:
    return [_julgar(d, _extrair_ec2) for d in _dirs(FIXTURES_EC2)]


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

    def test_todo_documento_do_catalogo_declara_area(self, catalogo):
        arquivos = {r["_source_file"] for r in catalogo}
        mapa = _area_por_arquivo()
        sem_area = sorted(arquivos - set(mapa))
        assert not sem_area, (
            f"{sem_area} nao declaram `area:` no cabecalho. Sem ela, as regras do "
            f"arquivo nao pertencem a area nenhuma e escapam de toda fronteira "
            f"medida por documento -- inclusive desta."
        )

    def test_area_do_documento_e_area_do_id_concordam(self, catalogo):
        """A guarda contra regra nova no arquivo errado.

        Uma `SF-EMRS-007` escrita dentro de `emr-infra.yaml` herdaria a area
        `SF-EMR` do documento e sairia do recorte de `SF-EMRS` sem que ninguem
        notasse -- a fronteira continuaria verde sobre uma regra que ela nunca
        olhou. Divergir entre as duas leituras e o defeito; a mensagem diz qual
        arquivo.
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

    def test_prefixo_de_id_nao_discrimina_as_duas_areas(self, catalogo):
        """A armadilha, provada em vez de comentada.

        `startswith("SF-EMR")` classifica toda regra Serverless como EC2. O teste
        existe para que, se alguem trocar a comparacao exata por prefixo, exista
        um lugar que ja disse por que aquilo nao funciona.
        """
        serverless = [r["id"] for r in _regras_da_area(catalogo, SERVERLESS)]
        assert serverless, "nenhuma regra SF-EMRS no catalogo: nao ha o que comparar"
        enganados = [rid for rid in serverless if rid.startswith(EC2)]
        assert enganados == serverless, (
            "esperava que todo id SF-EMRS casasse `startswith('SF-EMR')`. Se isso "
            "deixou de valer, a armadilha mudou de forma e este arquivo precisa "
            "ser relido, nao so ajustado."
        )
        assert all(_area_do_id(rid) != EC2 for rid in serverless), (
            "a comparacao exata deixou de separar as duas areas -- que e a unica "
            "coisa que impede este arquivo de provar o oposto do que promete."
        )


class TestNenhumaAreaLeONamespaceDaVizinha:
    """A fronteira no CATALOGO, antes de qualquer fixture.

    Recorte do precedente de `test_dq_investigation_end_to_end.py:194`, e aqui
    ele funciona pela mesma razao: os prefixos sao disjuntos. `emrs.` nao comeca
    com `emr.` porque o ponto esta no lugar certo -- e foi por isso que a Task 2
    escolheu `emrs.` em vez de `emr.serverless.` (D-5d-1).
    """

    def test_os_dois_namespaces_sao_disjuntos_por_prefixo(self):
        assert not NAMESPACE[SERVERLESS].startswith(NAMESPACE[EC2])
        assert not NAMESPACE[EC2].startswith(NAMESPACE[SERVERLESS])

    @pytest.mark.parametrize("area", [EC2, SERVERLESS])
    def test_nenhuma_regra_le_kind_da_area_vizinha(self, catalogo, area):
        vizinha = SERVERLESS if area == EC2 else EC2
        alheio = NAMESPACE[vizinha]
        regras = _regras_da_area(catalogo, area)
        assert regras, f"nenhuma regra na area {area}"
        for regra in regras:
            invasores = sorted(k for k in _kinds_lidos(regra) if k.startswith(alheio))
            assert not invasores, (
                f"{regra['id']} le {invasores}, do namespace de {vizinha}. Cada area "
                f"julga os facts do seu proprio extrator: `get-application` e "
                f"`describe-cluster` descrevem modelos de execucao diferentes, e "
                f"regra que le os dois produz achado que cita evidencia de outra "
                f"coisa."
            )

    @pytest.mark.parametrize("area", [EC2, SERVERLESS])
    def test_toda_regra_exige_ao_menos_um_kind_do_proprio_namespace(self, catalogo, area):
        """O que faz a fronteira ser por CONSTRUCAO e nao por sorte.

        `judge` pula regra cujo `requires_facts` nao esta presente. Se uma regra
        de qualquer das duas areas nao exigir nenhum kind do seu namespace, ela
        seria AVALIADA sobre o artefato do vizinho, e o silencio passaria a
        depender do `when` -- que e onde erro de regra mora.
        """
        proprio = NAMESPACE[area]
        for regra in _regras_da_area(catalogo, area):
            exigidos = set(regra.get("requires_facts") or [])
            assert any(k.startswith(proprio) for k in exigidos), (
                f"{regra['id']} nao exige nenhum kind `{proprio}*` em "
                f"`requires_facts` (exige {sorted(exigidos)}). Sem isso a regra "
                f"chega a ser avaliada sobre o artefato do outro modelo de "
                f"execucao, e a fronteira deixa de ser por construcao."
            )


class TestOsDoisCorporaEstaoVivos:
    """Sem isto, os dois testes de fronteira passariam com extracao quebrada.

    Zero achado dos dois lados satisfaz "nenhum achado da area vizinha" -- e
    seria verde sobre nada. Estes dois testes exigem que cada corpus dispare a
    SUA propria area antes de qualquer afirmacao sobre a de fora.
    """

    def test_o_corpus_serverless_dispara_a_area_serverless(self, catalogo, sobre_serverless):
        disparadas = {f.rule_id for j in sobre_serverless for f in j["findings"]}
        esperadas = {r["id"] for r in _regras_da_area(catalogo, SERVERLESS)}
        assert esperadas <= disparadas, (
            f"regras {sorted(esperadas - disparadas)} nao dispararam em nenhuma "
            f"fixture de `fixtures/emr_serverless/`. A fronteira medida sobre um "
            f"corpus mudo nao mede nada."
        )

    def test_o_corpus_ec2_dispara_a_area_ec2(self, catalogo, sobre_ec2):
        disparadas = {f.rule_id for j in sobre_ec2 for f in j["findings"]}
        esperadas = {r["id"] for r in _regras_da_area(catalogo, EC2)}
        assert esperadas <= disparadas, (
            f"regras {sorted(esperadas - disparadas)} nao dispararam em nenhuma "
            f"fixture de `fixtures/emr/`. A fronteira medida sobre um corpus mudo "
            f"nao mede nada."
        )


class TestFronteiraEntreAsDuasAreas:
    """§10.5 do spec, nas duas direcoes."""

    def test_nenhuma_regra_emr_dispara_sobre_serverless(self, catalogo, sobre_serverless):
        vetadas = {r["id"] for r in _regras_da_area(catalogo, EC2)}
        assert sobre_serverless, "corpus de EMR Serverless vazio"
        invasoes = sorted(
            (j["nome"], f.rule_id, tuple(f.evidence))
            for j in sobre_serverless
            for f in j["findings"]
            if f.rule_id in vetadas
        )
        assert not invasoes, (
            f"regra de EMR on EC2 disparou sobre `get-application`: {invasoes}. O "
            f"achado cita fact de uma application Serverless para falar de grupo de "
            f"instancia, purchasing option ou bootstrap action -- coisas que nao "
            f"existem nesse modelo de execucao."
        )

    def test_nenhuma_regra_emrs_dispara_sobre_ec2(self, catalogo, sobre_ec2):
        vetadas = {r["id"] for r in _regras_da_area(catalogo, SERVERLESS)}
        assert sobre_ec2, "corpus de EMR on EC2 vazio"
        invasoes = sorted(
            (j["nome"], f.rule_id, tuple(f.evidence))
            for j in sobre_ec2
            for f in j["findings"]
            if f.rule_id in vetadas
        )
        assert not invasoes, (
            f"regra de EMR Serverless disparou sobre `describe-cluster`: {invasoes}. "
            f"Um cluster nao tem capacidade pre-inicializada nem janela de "
            f"auto-stop; o achado cobraria do operador uma configuracao que a API "
            f"do modelo dele nao aceita."
        )


class TestOSilencioNaoEPorEscopo:
    """O verde pior que vermelho, fechado dos dois lados.

    `judge` pula por tres motivos, e so um deles e a fronteira. `runtime_scope` e
    `blocked_on` calam a regra ANTES de olhar para os facts -- se fosse por eles,
    os dois testes acima passariam sem que a regra vizinha tivesse chegado perto
    do artefato. `requires_facts` e o motivo legitimo, e e a fronteira por
    construcao acontecendo.

    A direcao EC2 e a que corre risco real: as fixtures de `fixtures/emr/` julgam
    com `runtime` declarado (`emr: "6.15.0"` e afins), nao com `{}`.
    """

    @pytest.mark.parametrize("area", [EC2, SERVERLESS])
    def test_a_area_vizinha_nunca_e_pulada_por_escopo_ou_bloqueio(
        self, catalogo, sobre_serverless, sobre_ec2, area
    ):
        corpus = sobre_serverless if area == EC2 else sobre_ec2
        vizinha = {r["id"] for r in _regras_da_area(catalogo, area)}
        culpados = sorted(
            (j["nome"], j["runtime"], s["rule_id"], s["reason"])
            for j in corpus
            for s in j["skipped"]
            if s["rule_id"] in vizinha and s["reason"] in {"runtime_scope", "blocked_on"}
        )
        assert not culpados, (
            f"regra de {area} calada por `{{runtime_scope, blocked_on}}` sobre o "
            f"artefato do outro modelo: {culpados}. A fronteira ficaria verde sem "
            f"nunca ter sido avaliada -- e voltaria a vermelho no dia em que o "
            f"escopo mudasse, longe daqui."
        )

    @pytest.mark.parametrize("area", [EC2, SERVERLESS])
    def test_toda_regra_vizinha_e_calada_por_falta_de_fact(
        self, catalogo, sobre_serverless, sobre_ec2, area
    ):
        """A afirmacao positiva: nao e que a regra nao disparou, e que ela foi
        alcancada e nao teve com que se sustentar. Toda regra da area vizinha,
        em toda fixture, aparece em `skipped` com `reason: requires_facts`."""
        corpus = sobre_serverless if area == EC2 else sobre_ec2
        vizinha = {r["id"] for r in _regras_da_area(catalogo, area)}
        for j in corpus:
            por_falta = {
                s["rule_id"] for s in j["skipped"] if s["reason"] == "requires_facts"
            }
            faltando = sorted(vizinha - por_falta)
            # So os skips da area vizinha na mensagem: despejar os 60+ skips
            # legitimos das outras doze areas esconde a linha que importa.
            visto = [s for s in j["skipped"] if s["rule_id"] in vizinha]
            assert not faltando, (
                f"em `{j['nome']}`, as regras {faltando} da area {area} nao foram "
                f"puladas por `requires_facts`. Ou elas foram avaliadas sobre o "
                f"artefato do outro modelo de execucao, ou foram caladas por outro "
                f"motivo. Skips da area {area} nesta fixture: {visto}"
            )
