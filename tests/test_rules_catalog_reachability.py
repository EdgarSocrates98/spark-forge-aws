"""Toda regra do catalogo precisa ser alcancavel, ou dizer que nao e.

O motor (`sparkforge/rules/engine.py`) reporta uma regra nao avaliada de duas
formas, e a diferenca e operacional, nao cosmetica:

    requires_facts -> "dispara assim que voce coletar o artefato"
    blocked_on     -> "nao dispara ate alguem construir o extrator"

Uma regra que exige um fact kind que NENHUM extrator emite, e que nao carrega
`blocked_on`, e reportada como `requires_facts`. Isso instrui o operador a
coletar um dado que nao esta a caminho, e ele espera por ele. Foi exatamente o
que aconteceu com as cinco regras SF-PQ-*, que dependem de `s3.prefix_summary`
e `plan.file_scan` -- dois kinds sem extrator nenhum -- e ficaram anos
parecendo apenas "sem dados coletados".

Estes testes fecham essa classe de drift na origem: uma regra nova que
referencie um kind inexistente falha aqui, em vez de virar uma espera
silenciosa meses depois.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.facts import (
    athena_workgroup,
    call_graph,
    catalog_schema,
    event_log,
    fusion,
    iceberg_metadata,
    pyspark_ast,
    runtime_detect,
    sql_literal,
    terraform,
)
from sparkforge.rules.loader import catalog_dir, load_catalog

EXTRACTORS = (
    athena_workgroup,
    call_graph,
    catalog_schema,
    event_log,
    fusion,
    iceberg_metadata,
    pyspark_ast,
    runtime_detect,
    sql_literal,
    terraform,
)

EMITTABLE: frozenset[str] = frozenset().union(*(m.EMITTED_KINDS for m in EXTRACTORS))

RULES = load_catalog(catalog_dir())
RULE_IDS = [r["id"] for r in RULES]


def _referenced_kinds(condition_group: dict) -> tuple[set[str], set[str]]:
    """(kinds exigidos presentes, kinds exigidos ausentes) de um bloco `when`."""
    present: set[str] = set()
    absent: set[str] = set()
    for group in ("all", "any"):
        for condition in condition_group.get(group) or []:
            if "fact" in condition:
                present.add(condition["fact"])
            if "absent" in condition:
                absent.add(condition["absent"])
    return present, absent


def test_o_registro_de_kinds_nao_esta_vazio() -> None:
    """Guarda contra o teste passar por nao ter carregado nada."""
    assert len(EMITTABLE) >= 50, sorted(EMITTABLE)
    assert len(RULES) >= 40, len(RULES)


@pytest.mark.parametrize("rule", RULES, ids=RULE_IDS)
def test_kind_exigido_tem_extrator_ou_a_regra_declara_blocked_on(rule: dict) -> None:
    required = set(rule.get("requires_facts") or [])
    present, _ = _referenced_kinds(rule.get("when") or {})
    orphans = sorted((required | present) - EMITTABLE)
    if not orphans:
        return
    assert rule.get("blocked_on"), (
        f"{rule['id']} exige {orphans}, que nenhum extrator emite, e nao declara "
        f"`blocked_on`. Sem isso o judge reporta 'requires_facts' e o operador "
        f"espera por um artefato que ninguem vai conseguir coletar. Ou construa o "
        f"extrator, ou marque a regra com `blocked_on: <capacidade-que-falta>`."
    )


@pytest.mark.parametrize("rule", RULES, ids=RULE_IDS)
def test_condicao_absent_nao_e_vacuamente_verdadeira(rule: dict) -> None:
    """`absent:` sobre um kind que ninguem emite dispara em QUALQUER entrada.

    Nao e silencio: e falso positivo sistematico. A regra acusa todo mundo,
    inclusive quem esta configurado corretamente, e acusar configuracao correta
    destroi a confianca no resto do relatorio.
    """
    _, absent = _referenced_kinds(rule.get("when") or {})
    orphans = sorted(absent - EMITTABLE)
    if not orphans:
        return
    assert rule.get("blocked_on"), (
        f"{rule['id']} testa `absent:` sobre {orphans}, que nenhum extrator emite. "
        f"A condicao e vacuamente verdadeira, entao a regra dispara em toda entrada. "
        f"Precisa de um fact sentinela que prove que o artefato foi analisado."
    )


def test_toda_regra_bloqueada_explica_o_bloqueio_em_comentario() -> None:
    """`blocked_on` sozinho nao diz por que a capacidade falta.

    Nao da para verificar automaticamente que um `blocked_on` e legitimo: o
    bloqueio nem sempre e um kind faltando. SF-ICE-004 tem todos os kinds, e
    esta bloqueada por um ATRIBUTO (`written_before_sort_order`) que exigiria
    comparar dois instantes no tempo -- granularidade que uma checagem de kind
    nao enxerga. O que da para exigir e que alguem tenha escrito o motivo perto
    da regra, para que a proxima pessoa nao precise redescobrir por que ela
    nunca dispara.
    """
    for path in sorted(Path(catalog_dir()).glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        rules = _rules_of(path)
        # Area inteiramente bloqueada e explicada uma vez no cabecalho, nao
        # cinco vezes: repetir o mesmo paragrafo por regra e ruido, e o teste
        # de cabecalho abaixo ja cobre esse caso.
        if rules and all(r.get("blocked_on") for r in rules):
            continue
        for rule in rules:
            blocker = rule.get("blocked_on")
            if not blocker:
                continue
            before = text.split(f"- id: {rule['id']}")[0]
            preamble = before.rsplit("\n\n", 1)[-1]
            assert "#" in preamble, (
                f"{rule['id']} declara `blocked_on: {blocker}` sem nenhum comentario "
                f"logo acima explicando qual capacidade falta e por que. Sem isso a "
                f"regra vira ruido permanente: ninguem sabe se ainda faz sentido."
            )


def test_area_inteiramente_inerte_avisa_no_cabecalho() -> None:
    """Quem abre `parquet.yaml` e ve que nada dispara merece saber no topo."""
    for path in sorted(Path(catalog_dir()).glob("*.yaml")):
        rules = _rules_of(path)
        if not rules or not all(r.get("blocked_on") for r in rules):
            continue
        header = path.read_text(encoding="utf-8").split("rules:")[0]
        assert "blocked_on" in header, (
            f"{path.name}: todas as {len(rules)} regras estao bloqueadas, mas o "
            f"cabecalho nao explica que a area inteira esta inerte hoje."
        )


def _rules_of(path: Path) -> list[dict]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("rules") or []
