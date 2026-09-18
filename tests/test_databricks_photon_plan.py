"""Photon reconhecido no plano, e a recusa movida pelo artefato."""
from pathlib import Path

import yaml

from sparkforge.facts.spark_plan import extract_plan, extract_plan_path
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
PLANOS = ROOT / "fixtures" / "plan"


def _facts(caso: str):
    entrada = PLANOS / caso / "input"
    return extract_plan_path(entrada / "plan.txt", repo_root=entrada)


def test_plano_photon_gera_fact_de_photon():
    photon = [f for f in _facts("photon_join") if f.kind == "plan.photon"]
    assert len(photon) == 1
    fact = photon[0]
    assert fact.measures["photon_operators"] == 16
    assert fact.measures["operators"] == 17
    assert "PhotonBroadcastHashJoin" in fact.attrs["operators"]
    assert fact.attrs["operators"] == sorted(set(fact.attrs["operators"]))
    assert fact.attrs["explanation"] == "The query is fully supported by Photon."
    udf = [f for f in _facts("photon_udf") if f.kind == "plan.photon"]
    assert udf[0].measures["photon_operators"] == 7


def test_plano_photon_so_arvore_conta_cada_no_uma_vez():
    """Regressao: o caminho so-arvore (`_parse_simple`, sem blocos numerados de
    detalhe) conta cada no do Photon uma unica vez -- mesma contagem do
    caminho formatado (`fixtures/plan/photon_join`), so que sem os blocos
    `(n) Nome`.
    """
    texto = """== Physical Plan ==
AdaptiveSparkPlan (17)
+- == Initial Plan ==
   PhotonResultStage (16)
   +- PhotonColumnarToRow (15)
      +- PhotonProject (14)
         +- PhotonBroadcastHashJoin Inner (13)
            :- PhotonGroupingAgg (7)
            :  +- PhotonShuffleExchangeSource (6)
            :     +- PhotonShuffleMapStage (5)
            :        +- PhotonShuffleExchangeSink (4)
            :           +- PhotonGroupingAgg (3)
            :              +- PhotonProject (2)
            :                 +- PhotonRange (1)
            +- PhotonShuffleExchangeSource (12)
               +- PhotonShuffleMapStage (11)
                  +- PhotonShuffleExchangeSink (10)
                     +- PhotonProject (9)
                        +- PhotonRange (8)

== Photon Explanation ==
The query is fully supported by Photon.
"""
    facts = extract_plan(texto, "plan.txt")
    photon = [f for f in facts if f.kind == "plan.photon"]
    assert len(photon) == 1
    fact = photon[0]
    assert fact.measures["photon_operators"] == 16
    assert fact.measures["operators"] == 17
    formatado = [f for f in _facts("photon_join") if f.kind == "plan.photon"][0]
    assert fact.attrs["operators"] == formatado.attrs["operators"]
    assert fact.attrs["explanation"] == "The query is fully supported by Photon."


def test_plano_sem_photon_nao_muda_veredito():
    for caso in sorted(p.name for p in PLANOS.iterdir() if p.is_dir()):
        if caso.startswith("photon_"):
            continue
        facts = _facts(caso)
        assert not any(f.kind == "plan.photon" for f in facts), caso
        meta = yaml.safe_load((PLANOS / caso / "meta.yaml").read_text(encoding="utf-8"))
        obtido = sorted(
            (f.rule_id, f.severity, repr(sorted(f.subject.items())))
            for f in judge(facts, load_catalog(), meta["runtime"])
        )
        esperado = sorted(
            (f["rule_id"], f["severity"], repr(sorted(f["subject"].items())))
            for f in __import__("json").loads(
                (PLANOS / caso / "expected" / "findings.json").read_text(encoding="utf-8")
            )
        )
        assert obtido == esperado, caso
