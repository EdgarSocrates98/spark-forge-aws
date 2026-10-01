"""A fronteira da area `SF-CTM`, medida nas duas direcoes.

`tests/test_emr_eks_area_boundary.py` mede a fronteira entre as tres areas de
EMR com uma tabela de plataformas, porque ali as tres leem artefatos PARECIDOS --
tres dumps de API da AWS, com vocabulario que se confunde. Aqui o risco e outro,
e por isso o arquivo e outro: `SF-CTM` le uma definicao de job de um produto que
nao e AWS, nao roda Spark e nao tem cluster. Uma regra de EMR ou de Glue
disparando sobre ela produziria um achado com vocabulario de outro universo --
purchasing option, worker type, format version do Iceberg -- sobre um JSON que
nao tem nada disso.

Este arquivo nao replica a tabela: ele deriva o que testa da ARVORE de fixtures,
entao corpus novo entra na conta sozinho -- o oposto de uma lista que alguem
precisa lembrar de estender.

**Em DOIS niveis, e a divisao e de custo MEDIDO.** `judge` sobre o catalogo
inteiro nao e barato, e o repositorio tem quase 250 fixtures com golden: julgar
todas levava tres minutos so neste arquivo. Entao:

- o invariante BARATO roda sobre TODAS elas -- nenhum golden fora de
  `fixtures/controlm/` carrega kind `ctm.*`, e sem kind `ctm.*` o
  `requires_facts` de `SF-CTM-001` nao tem como ser satisfeito. E a rede larga,
  e nenhuma fixture escapa dela;
- o invariante CARO -- julgar de verdade, com o catalogo inteiro e o runtime da
  propria fixture -- roda sobre UMA amostra por corpus, mais o corpus de
  Control-M inteiro. E ele que prova que o silencio vem de `requires_facts` e
  nao de guarda de versao.

Fixture nova num corpus ja coberto entra na rede larga; corpus novo entra nas
duas, porque a amostra e derivada dos diretorios.

**As tres armadilhas que decidem se ele mede alguma coisa.**

1. Verde por skip. `judge` nao avalia regra fora de `runtime_scope` nem regra
   `blocked_on`, e regra nao avaliada nao dispara. Por isso
   `TestOSilencioVemDeRequiresFacts` afirma sobre a lista de `skipped`: o
   silencio de `SF-CTM` fora do corpus dela tem de vir de `requires_facts` --
   ausencia dos kinds `ctm.*` --, nunca de escopo de versao. Fronteira por
   construcao e fronteira; fronteira por guarda de versao some no dia em que
   alguem declarar a versao certa.

2. Verde sobre corpus mudo. Zero achado dos dois lados satisfaz "nenhum achado
   da area vizinha". `TestOCorpusEstaVivo` exige que `SF-CTM-001` dispare de
   fato em algum lugar antes de qualquer afirmacao sobre o que ela NAO faz.

3. Prefixo. `SF-CTM` nao e prefixo de nenhuma area existente e nenhuma e prefixo
   dele -- conferido em `test_a_area_nao_colide_por_prefixo` --, mas a
   classificacao aqui e por `rsplit("-", 1)` sobre o `rule_id`, que e a mesma
   conta que `findings_area` do roteamento usa. Comparar por `startswith` foi o
   defeito medido em `SF-EMR`/`SF-EMRS`/`SF-EMRK`, e nao se repete aqui.
"""
from __future__ import annotations

import json
from functools import cache, lru_cache
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters._core import _facts_from_dicts
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
CORPUS_CTM = FIXTURES / "controlm"

AREA = "SF-CTM"


def _area_de(rule_id: str) -> str:
    """`SF-CTM-001` -> `SF-CTM`. A MESMA conta de `findings_area` no roteamento.

    `rsplit` e nao `startswith`: `SF-EMR` e prefixo de `SF-EMRS` e de `SF-EMRK`,
    e classificar por prefixo fez exatamente esse par de areas ser medido ao
    contrario antes de alguem perceber.
    """
    return rule_id.rsplit("-", 1)[0]


@lru_cache(maxsize=1)
def _fixtures_com_golden() -> tuple[Path, ...]:
    """Todo diretorio de fixture com `meta.yaml` e `expected/facts.json`.

    Derivado da arvore, nunca de lista escrita a mao: corpus novo entra na
    fronteira sozinho, que e o oposto de uma tabela que alguem precisa lembrar de
    estender.
    """
    achados = [
        meta.parent
        for meta in FIXTURES.rglob("meta.yaml")
        if (meta.parent / "expected" / "facts.json").is_file()
    ]
    return tuple(sorted(achados))


@lru_cache(maxsize=1)
def _amostra_por_corpus() -> tuple[Path, ...]:
    """Uma fixture por corpus, fora do de Control-M -- a populacao do teste CARO.

    A escolha dentro do corpus e a que declara MAIS regras em `expects_rules`, e
    nao a primeira em ordem alfabetica: fixture saudavel satisfaz "nenhuma regra
    de fora disparou" por vacuidade, e a fronteira precisa valer tambem quando ha
    achado. Empate resolve pelo nome, para a amostra ser deterministica.

    O criterio le o `meta.yaml` e NAO chama `judge`, e a diferenca e de custo
    medido: escolher por `len(judge(...))` obrigaria a julgar todas as fixtures
    do repositorio so para decidir quais julgar -- exatamente os tres minutos que
    a divisao em dois niveis existe para nao pagar. `expects_rules` e a mesma
    informacao, ja declarada, e os `test_fixtures_golden_*` travam que ela e
    verdadeira.
    """
    por_corpus: dict[str, list[Path]] = {}
    for directory in _fixtures_com_golden():
        if CORPUS_CTM in directory.parents:
            continue
        por_corpus.setdefault(directory.parent.name, []).append(directory)

    def _quantas_regras(directory: Path) -> int:
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8")) or {}
        return len(meta.get("expects_rules") or [])

    escolhidas = []
    for _, candidatas in sorted(por_corpus.items()):
        escolhidas.append(max(sorted(candidatas), key=_quantas_regras))
    return tuple(escolhidas)


@cache
def _julga(directory: Path):
    """Julga os facts do GOLDEN commitado, com o runtime da propria fixture.

    Os facts vem do golden e nao de reextracao: reextrair mediria os extratores
    de novo -- coisa que os `test_fixtures_golden_*` ja fazem -- e faria este
    arquivo depender de vinte e tantos extratores para afirmar sobre regras.

    O `runtime` sai do `meta.yaml` da propria fixture porque ele DIFERE entre
    corpora, e julgar tudo com um runtime unico pularia regras por escopo e
    produziria silencio que este arquivo leria como fronteira.

    CACHEADA porque as tres classes deste arquivo perguntam sobre o MESMO
    conjunto de fixtures, e `judge` sobre o catalogo inteiro nao e barato: sem o
    cache, cada fixture do repositorio seria julgada tres vezes para responder
    tres perguntas sobre o mesmo resultado.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    dicts = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
    facts = _facts_from_dicts(dicts)
    return judge(facts, load_catalog(), meta.get("runtime") or {}, return_skipped=True)


class TestOCorpusEstaVivo:
    """Sem isto, tudo abaixo passa sobre nada."""

    def test_a_area_existe_no_catalogo(self):
        areas = {_area_de(r["id"]) for r in load_catalog()}
        assert AREA in areas

    def test_a_area_nao_colide_por_prefixo_com_nenhuma_outra(self):
        """`SF-EMR` e prefixo de `SF-EMRS` e de `SF-EMRK`, e isso ja fez uma
        fronteira ser medida ao contrario. `SF-CTM` nao pode repetir o caso."""
        areas = sorted({_area_de(r["id"]) for r in load_catalog()})
        outras = [a for a in areas if a != AREA]
        assert not [a for a in outras if a.startswith(AREA)], (
            f"{AREA} e prefixo de {[a for a in outras if a.startswith(AREA)]}"
        )
        assert not [a for a in outras if AREA.startswith(a)], (
            f"{[a for a in outras if AREA.startswith(a)]} e prefixo de {AREA}"
        )

    def test_toda_regra_da_area_dispara_em_alguma_fixture_da_area(self):
        """Fronteira so vale se houver achado dos dois lados. Uma area que nunca
        dispara satisfaz 'nao dispara fora do corpus dela' por vacuidade."""
        esperadas = {r["id"] for r in load_catalog() if _area_de(r["id"]) == AREA}
        vistas: set[str] = set()
        for directory in sorted(p for p in CORPUS_CTM.iterdir() if p.is_dir()):
            findings, _ = _julga(directory)
            vistas |= {f.rule_id for f in findings}
        assert esperadas <= vistas, sorted(esperadas - vistas)


class TestARedeLarga:
    """O invariante barato, sobre TODAS as fixtures com golden.

    `SF-CTM-001` exige `ctm.job` e `ctm.version_declared`. Um golden de outra
    area que carregue kind `ctm.*` seria a UNICA porta pela qual a regra poderia
    disparar fora do corpus dela -- e fecha-la custa uma leitura de JSON por
    fixture, contra um `judge` inteiro sobre o catalogo.
    """

    def test_nenhum_golden_de_fora_carrega_kind_ctm(self):
        from sparkforge.facts.controlm_jobs import EMITTED_KINDS

        intrusos: dict[str, list[str]] = {}
        for directory in _fixtures_com_golden():
            if CORPUS_CTM in directory.parents:
                continue
            dicts = json.loads(
                (directory / "expected" / "facts.json").read_text(encoding="utf-8")
            )
            vistos = sorted({f["kind"] for f in dicts} & set(EMITTED_KINDS))
            if vistos:
                intrusos[f"{directory.parent.name}/{directory.name}"] = vistos
        assert not intrusos, intrusos

    def test_o_corpus_ctm_so_carrega_kind_ctm(self):
        """O espelho, e ele fecha a porta oposta: golden de Control-M com kind de
        outro extrator faria regra de fora disparar ali."""
        from sparkforge.facts.controlm_jobs import EMITTED_KINDS

        for directory in sorted(p for p in CORPUS_CTM.iterdir() if p.is_dir()):
            dicts = json.loads(
                (directory / "expected" / "facts.json").read_text(encoding="utf-8")
            )
            fora = sorted({f["kind"] for f in dicts} - set(EMITTED_KINDS))
            assert not fora, f"{directory.name}: {fora}"


@pytest.mark.parametrize(
    "directory",
    _amostra_por_corpus(),
    ids=[f"{p.parent.name}/{p.name}" for p in _amostra_por_corpus()],
)
def test_nenhuma_regra_ctm_dispara_fora_do_corpus_dela(directory: Path):
    """Direcao 1, com julgamento REAL: regra de Control-M sobre artefato de outra
    area.

    Um `SF-CTM-001` sobre um dump de EMR ou sobre um `.tf` diria que um job do
    Control-M usa capacidade que a versao nao tem -- sobre um artefato onde nao
    ha job do Control-M nenhum.
    """
    findings, _ = _julga(directory)
    intrusas = sorted({f.rule_id for f in findings if _area_de(f.rule_id) == AREA})
    assert not intrusas, (
        f"{intrusas} dispararam sobre {directory.parent.name}/{directory.name}, "
        f"que nao e artefato de Control-M"
    )


@pytest.mark.parametrize(
    "directory",
    sorted(p for p in CORPUS_CTM.iterdir() if p.is_dir()),
    ids=[p.name for p in sorted(p for p in CORPUS_CTM.iterdir() if p.is_dir())],
)
def test_nenhuma_regra_de_outra_area_dispara_sobre_o_corpus_ctm(directory: Path):
    """Direcao 2, e ela e a que mais importa aqui.

    Os facts de uma definicao `Jobs-as-Code` sao todos `ctm.*`, e nenhuma regra
    das outras areas os exige -- entao a fronteira e POR CONSTRUCAO, e nao por
    supressao. Se alguma regra de fora aparecer, o defeito e um `requires_facts`
    largo demais em outra area, nao uma excecao a escrever aqui.
    """
    findings, _ = _julga(directory)
    intrusas = sorted({f.rule_id for f in findings if _area_de(f.rule_id) != AREA})
    assert not intrusas, (
        f"{intrusas} dispararam sobre {directory.name}, que so tem facts `ctm.*`"
    )


class TestOSilencioVemDeRequiresFacts:
    """Fronteira por CONSTRUCAO, e nao por guarda de versao.

    Se `SF-CTM` estivesse calada fora do corpus dela por `runtime_scope`, a
    fronteira sumiria no dia em que alguem declarasse um runtime que a satisfaca
    -- e a regra passaria a acusar dumps de EMR sem que nada tivesse mudado nela.
    """

    def test_o_skip_fora_do_corpus_e_por_requires_facts(self):
        fora = _amostra_por_corpus()
        assert fora, "sem fixture de outra area nao ha o que medir"
        razoes: set[str] = set()
        for directory in fora:
            _, skipped = _julga(directory)
            razoes |= {
                s["reason"] for s in skipped if _area_de(str(s.get("rule_id", ""))) == AREA
            }
        assert razoes == {"requires_facts"}, sorted(razoes)
