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
from pathlib import Path

import pytest

from sparkforge.facts import (
    athena_workgroup,
    call_graph,
    catalog_schema,
    consumers,
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
    "call_graph": call_graph,
    "catalog_schema": catalog_schema,
    "consumers": consumers,
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
