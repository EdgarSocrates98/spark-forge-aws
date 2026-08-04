"""Todo kind que algum extrator emite precisa aparecer em algum golden.

Esta e a guarda que faltava. `test_rules_catalog_reachability.py` fecha a
ponta oposta -- regra que exige kind que ninguem emite -- mas nada verificava o
inverso: kind emitido que NENHUMA fixture exercita. Era o caso de 17 kinds,
entre eles os quatro de `callgraph.*`, os tres de `athena.*`, o
`env.runtime_signal` que alimenta SF-ENV-001 (P0) e SF-ENV-004 (P1), e quatro
dos `*.unresolved` -- justamente a maquinaria de ponto cego, que quando para
de contar nao levanta erro nenhum: ela simplesmente devolve zero, e zero e
indistinguivel de "esta tudo resolvido".

Um kind sem golden e um contrato que pode sumir numa refatoracao sem nenhum
teste reclamar. A regra do repo (`rules/catalog/README.md`, item 6) ja exigia
fixture por REGRA; este modulo estende a mesma exigencia aos facts que nao
alimentam regra nenhuma -- que sao os mais faceis de perder, porque ninguem
sente falta deles ate um agente precisar.
"""
import json
import re
from pathlib import Path

import pytest

from sparkforge.facts import (
    athena_workgroup,
    benchmark,
    call_graph,
    catalog_schema,
    consumers,
    data_quality,
    emr_cluster,
    event_log,
    fusion,
    iceberg_metadata,
    pyspark_ast,
    runtime_detect,
    s3_listing,
    spark_plan,
    sql_literal,
    terraform,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"

EXTRACTORS = {
    "athena_workgroup": athena_workgroup,
    "benchmark": benchmark,
    "call_graph": call_graph,
    "catalog_schema": catalog_schema,
    "consumers": consumers,
    "data_quality": data_quality,
    "emr_cluster": emr_cluster,
    "event_log": event_log,
    "fusion": fusion,
    "iceberg_metadata": iceberg_metadata,
    "pyspark_ast": pyspark_ast,
    "runtime_detect": runtime_detect,
    "s3_listing": s3_listing,
    "spark_plan": spark_plan,
    "sql_literal": sql_literal,
    "terraform": terraform,
}

EMITTABLE: frozenset[str] = frozenset().union(*(m.EMITTED_KINDS for m in EXTRACTORS.values()))


def _golden_files():
    return sorted(FIXTURES.glob("*/*/expected/facts.json"))


def _kinds_in_goldens() -> set[str]:
    kinds: set[str] = set()
    for path in _golden_files():
        for fact in json.loads(path.read_text(encoding="utf-8")):
            kinds.add(fact["kind"])
    return kinds


def test_the_corpus_is_not_empty():
    """Guarda contra o modulo inteiro passar por nao ter lido golden nenhum."""
    assert len(_golden_files()) >= 30
    assert len(EMITTABLE) >= 70


@pytest.mark.parametrize("name", sorted(EXTRACTORS))
def test_every_kind_of_every_extractor_appears_in_some_golden(name):
    covered = _kinds_in_goldens()
    missing = sorted(set(EXTRACTORS[name].EMITTED_KINDS) - covered)
    assert not missing, (
        f"{name}: kinds sem nenhuma fixture que os produza: {missing}. "
        "Crie uma fixture que exercite o kind, ou remova o kind de EMITTED_KINDS "
        "se ele nao e mais emitido."
    )


def test_no_golden_carries_a_kind_that_no_extractor_declares():
    """A direcao oposta: golden com kind fora de todo `EMITTED_KINDS` significa
    ou um extrator que emite fora do vocabulario declarado, ou um golden
    obsoleto que sobreviveu a remocao do kind."""
    unknown = sorted(_kinds_in_goldens() - EMITTABLE)
    assert not unknown, unknown


def test_every_unresolved_kind_is_exercised():
    """Recorte explicito sobre a maquinaria de ponto cego. Ela e a que mais
    silenciosamente apodrece: quando para de contar, devolve zero, e zero e
    exatamente o que uma extracao limpa devolve."""
    covered = _kinds_in_goldens()
    unresolved = {k for k in EMITTABLE if k.endswith(".unresolved")}
    assert unresolved, "nenhum kind de ponto cego encontrado -- o filtro quebrou"
    assert unresolved <= covered, sorted(unresolved - covered)


def _rules():
    from sparkforge.rules.loader import catalog_dir, load_catalog

    return [r for r in load_catalog(catalog_dir()) if r["id"].startswith("SF-")]


def _rules_fired_in_goldens() -> set[str]:
    fired: set[str] = set()
    for path in FIXTURES.glob("*/*/expected/findings.json"):
        for finding in json.loads(path.read_text(encoding="utf-8")):
            fired.add(finding["rule_id"])
    return fired


def test_every_rule_has_a_fixture_that_fires_it():
    """A contraparte do teste de kinds, no nivel da REGRA.

    `rules/catalog/README.md` item 6 ja exigia fixture por regra, mas nada
    verificava. Uma regra sem golden que a faca disparar nunca foi provada:
    ela pode ter limiar invertido, `where` que nao casa com nenhum fact real,
    ou `requires_facts` contraditorio -- foi exatamente o caso de SF-GLUE-005,
    que exigia `spark.stage.spill` presente E ausente ao mesmo tempo e por isso
    nao podia disparar nunca. O defeito sobreviveu porque estava atras de um
    `blocked_on`, e nenhum teste olhava.

    Regra que passe a nao disparar em nenhuma fixture quebra aqui, e a correcao
    e uma das duas: criar a fixture que a exercita, ou remover a regra.
    """
    missing = sorted({r["id"] for r in _rules()} - _rules_fired_in_goldens())
    assert not missing, (
        f"regras sem nenhuma fixture que as faca disparar: {missing}. "
        "Uma regra sem golden positivo nunca foi provada -- crie a fixture, "
        "ou remova a regra do catalogo."
    )


def test_no_golden_fires_a_rule_that_left_the_catalog():
    """A direcao oposta: golden que dispara regra inexistente e golden
    obsoleto, sobrevivente de uma remocao que ninguem regenerou."""
    unknown = sorted(_rules_fired_in_goldens() - {r["id"] for r in _rules()})
    assert not unknown, unknown


# --------------------------------------------------------------------------- #
# Todo dominio de fixture precisa de um modulo golden que o exercite
# --------------------------------------------------------------------------- #
#
# `scripts/verify_wheel.py` monta o gate de paridade assim:
#
#     GOLDEN_MODULES = sorted(p.name for p in (ROOT / "tests").glob("test_fixtures_*.py"))
#
# Derivado do disco, entao um modulo novo entra sozinho -- foi o que aconteceu
# com `test_fixtures_golden_emr.py` na Fase 5b. Mas a ponta oposta nao tinha
# guarda: um DIRETORIO de fixture sem modulo que o rode nao quebra nada. Ele
# fica no repositorio parecendo cobertura, o gate de wheel nunca o executa
# contra o pacote instalado, e a suite segue verde.
#
# E risco vivo, nao hipotetico: `docs/superpowers/STATUS.md` registra EMR
# Serverless e EMR on EKS como divida aberta, e as duas nascem como
# `fixtures/<dominio>/` novo. Esquecer o modulo golden e o erro natural.
#
# A mesma familia de defeito que este arquivo inteiro existe para impedir:
# ausencia que se parece com cobertura.

_FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
_TESTS_ROOT = Path(__file__).resolve().parent

# Aceita as duas grafias que o corpus usa hoje, e a segunda so por acidente
# historico: `pyspark` mora em `test_fixtures_golden.py`, sem sufixo.
_DOMINIO_SEM_SUFIXO = {"pyspark": "test_fixtures_golden.py"}


def _dominios_de_fixture() -> set[str]:
    return {p.name for p in _FIXTURES_ROOT.iterdir() if p.is_dir()}


def _dominios_reivindicados() -> dict[str, str]:
    """Dominio -> modulo que o exercita, lido do `FIXTURES = ROOT / "fixtures" / "<x>"`.

    Derivado do fonte, nunca de lista escrita a mao: lista a mao e mais um lugar
    para esquecer de atualizar, e o esquecimento seria invisivel.
    """
    padrao = re.compile(r'FIXTURES\s*=\s*ROOT\s*/\s*"fixtures"\s*/\s*"([a-z0-9_]+)"')
    reivindicados: dict[str, str] = {}
    for modulo in sorted(_TESTS_ROOT.glob("test_fixtures_golden*.py")):
        for dominio in padrao.findall(modulo.read_text(encoding="utf-8")):
            reivindicados[dominio] = modulo.name
    return reivindicados


def test_every_fixture_domain_has_a_golden_module():
    """Diretorio de fixture sem modulo golden e cobertura aparente.

    O gate de `verify_wheel.py` roda os modulos, nao os diretorios: um dominio
    que nenhum modulo carrega nunca e verificado contra o pacote instalado, e
    ninguem reclama.
    """
    reivindicados = _dominios_reivindicados()
    orfaos = sorted(_dominios_de_fixture() - set(reivindicados))
    assert not orfaos, (
        f"dominios de fixture sem modulo golden: {orfaos}. Crie "
        f"tests/test_fixtures_golden_<dominio>.py com "
        f'`FIXTURES = ROOT / "fixtures" / "<dominio>"` -- sem isso o corpus existe, '
        f"parece cobertura, e o gate de wheel nunca o executa."
    )


def test_no_golden_module_points_at_a_domain_that_does_not_exist():
    """A ponta oposta: modulo apontando para diretorio que sumiu."""
    reivindicados = _dominios_reivindicados()
    fantasmas = sorted(set(reivindicados) - _dominios_de_fixture())
    assert not fantasmas, (
        f"modulos golden apontam para dominios inexistentes: "
        f"{ {d: reivindicados[d] for d in fantasmas} }. O modulo passa sem verificar "
        f"nada, que e pior que falhar."
    )


def test_the_domain_map_is_not_vacuous():
    """Guarda do proprio invariante.

    Se o padrao de leitura parar de casar -- alguem troca aspas duplas por
    simples, ou usa uma variavel -- os dois testes acima passariam sobre
    conjuntos vazios e aprovariam qualquer coisa.
    """
    reivindicados = _dominios_reivindicados()
    assert len(reivindicados) >= 15, (
        f"so {len(reivindicados)} dominios reivindicados; o corpus tem "
        f"{len(_dominios_de_fixture())}. O padrao de leitura provavelmente parou de "
        f"casar, e os invariantes de dominio viraram assercao sobre conjunto vazio."
    )
    for dominio, modulo in _DOMINIO_SEM_SUFIXO.items():
        assert reivindicados.get(dominio) == modulo, (
            f"`{dominio}` deveria ser exercitado por {modulo}; a excecao historica "
            f"mudou e este mapa nao acompanhou."
        )
