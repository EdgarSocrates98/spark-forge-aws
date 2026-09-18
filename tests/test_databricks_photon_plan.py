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


def test_fact_de_photon_recusa_regra_de_plano_sem_declaracao():
    from sparkforge.findings.models import Fact

    base = _facts("photon_join")
    join = Fact(
        kind="plan.join",
        subject={"type": "plan_node", "file": "plan.txt", "line": 1, "symbol": "(1) X",
                 "node_id": 1, "operator": "CartesianProduct", "relation": ""},
        attrs={"strategy": "CartesianProduct"},
        provenance={"extractor": "teste"},
    )
    achados, pulados = judge([*base, join], load_catalog(), {"spark": "4.2.0"}, return_skipped=True)
    assert "SF-PLAN-003" not in {f.rule_id for f in achados}
    assert {"rule_id": "SF-PLAN-003", "reason": "databricks.photon.unresolved"} in pulados
    sem_photon = judge([join], load_catalog(), {"spark": "4.2.0"})
    assert "SF-PLAN-003" in {f.rule_id for f in sem_photon}


def test_udf_sob_photon_continua_julgada():
    achados = judge(_facts("photon_udf"), load_catalog(), {"spark": "4.2.0"})
    assert "SF-PLAN-002" in {f.rule_id for f in achados}
    aqe = judge(_facts("photon_join"), load_catalog(), {"spark": "4.2.0"})
    assert "SF-PLAN-004" in {f.rule_id for f in aqe}


def test_photon_off_contra_plano_photon_diverge():
    from sparkforge.adapters._core import build_runtime

    context, facts = build_runtime(databricks="19", photon="off", facts=_facts("photon_join"))
    assert context.photon == "on"
    assert any(d.startswith("photon:") for d in context.divergences)
    estado = next(f for f in facts if f.kind == "databricks.photon")
    assert (estado.attrs["state"], estado.attrs["source"]) == ("on", "plan")


def test_plano_photon_cala_sf_env_006():
    from sparkforge.adapters._core import build_runtime

    context, facts = build_runtime(databricks="19", facts=_facts("photon_join"))
    assert "SF-ENV-006" not in {f.rule_id for f in judge(facts, load_catalog(), context.to_dict())}
    _, sem_plano = build_runtime(databricks="19")
    assert "SF-ENV-006" in {f.rule_id for f in judge(sem_plano, load_catalog(), {"databricks": "19"})}


def test_plano_photon_sem_plataforma_nao_registra_fact_nem_diverge():
    """Sem `databricks=`, o plano Photon continua sendo lido -- a leitura vai
    para `sources["plan"]` e e tratada como observacao dentro de `_photon` --
    mas `_photon` so entra em `context.photon`/divergencia/fact sob a
    plataforma databricks. Sem plataforma nenhuma, a ausencia de declaracao
    nao gera nem divergencia nem fact -- ver o ramo `if not databricks` de
    `_photon` em `sparkforge/facts/runtime_detect.py`."""
    from sparkforge.adapters._core import build_runtime

    context, facts = build_runtime(facts=_facts("photon_join"))
    assert context.photon == ""
    assert not any(d.startswith("photon:") for d in context.divergences)
    assert not any(f.kind == "databricks.photon" for f in facts)


def test_plano_photon_com_declaracao_concordante_fica_sem_divergencia():
    """`--photon on` diante de um plano que ja mostra Photon concorda com a
    observacao: `context.photon` fica "on", a fonte do fact e "plan" (quem
    observou), e nao ha divergencia `photon:` -- so discordancia diverge."""
    from sparkforge.adapters._core import build_runtime

    context, facts = build_runtime(databricks="19", photon="on", facts=_facts("photon_join"))
    assert context.photon == "on"
    estado = next(f for f in facts if f.kind == "databricks.photon")
    assert estado.attrs == {"state": "on", "source": "plan"}
    assert not any(d.startswith("photon:") for d in context.divergences)


def test_plano_photon_declarado_sem_databricks_continua_divergindo():
    """`--photon on` sem `--databricks` e a declaracao sem plataforma que o
    ramo `if not databricks` de `_photon` marca como divergencia -- o plano
    Photon nao muda esse caminho, so acrescenta a fonte `plan` aos sources."""
    from sparkforge.adapters._core import build_runtime

    context, facts = build_runtime(photon="on", facts=_facts("photon_join"))
    assert context.photon == ""
    photon_divergencias = [d for d in context.divergences if d.startswith("photon:")]
    assert len(photon_divergencias) == 1
    assert "declarado sem plataforma databricks detectada" in photon_divergencias[0]
    assert not any(f.kind == "databricks.photon" for f in facts)


def test_databricks_do_event_log_com_plano_photon_sem_flag():
    """Plataforma databricks vinda do event log (mesmo formato de fact que
    `tests/test_databricks_platform.py::test_event_log_declara_plataforma_databricks`
    usa) mais um plano Photon, sem `--photon`: a observacao do plano decide
    sozinha, fonte "plan"."""
    from sparkforge.adapters._core import build_runtime
    from sparkforge.findings.models import Fact

    chave = "spark.databricks.clusterUsageTags.sparkVersion"
    evento = Fact(
        kind="spark.conf_effective",
        subject={"type": "job_run", "symbol": chave},
        attrs={
            "key": chave,
            "value": "15.4.x-scala2.12",
            "source_event": "SparkListenerEnvironmentUpdate",
        },
        provenance={"extractor": "event_log@0.1.0"},
    )
    context, facts = build_runtime(facts=[evento, *_facts("photon_join")])
    assert context.photon == "on"
    estado = next(f for f in facts if f.kind == "databricks.photon")
    assert estado.attrs == {"state": "on", "source": "plan"}


def test_arrow_eval_python_nao_afirma_pandas():
    udf = [f for f in _facts("photon_udf") if f.kind == "plan.python_udf"]
    assert [f.attrs["udf_type"] for f in udf] == ["arrow"]
    regra = next(r for r in load_catalog() if r["id"] == "SF-PLAN-002")
    achado = next(
        f for f in judge(_facts("photon_udf"), [regra], {"spark": "4.2.0"})
    )
    texto = " ".join(str(x) for x in (achado.explanation, *achado.proposed_change))
    assert "é `pandas_udf`" not in texto
    assert "pandas_udf já é a escolha certa" not in texto


def test_sf_plan_002_ainda_casa_udf_pandas():
    """O ramo `pandas` do `any` de SF-PLAN-002 (rules/catalog/spark-plan.yaml)
    nao tinha cobertura: nenhuma fixture ou teste tinha um no `*InPandas`. O
    fact e sintetico -- subject copiado de um `plan.python_udf` real extraido
    de `photon_udf`, trocando o operador Arrow por `MapInPandas`, cujo
    `udf_type` vem de `_PYTHON_UDF_OPERATORS` (sparkforge/facts/spark_plan.py)
    em vez de fixado a mao, para o teste cair se o mapeamento mudar."""
    from sparkforge.facts.spark_plan import _PYTHON_UDF_OPERATORS
    from sparkforge.findings.models import Fact

    real = next(f for f in _facts("photon_udf") if f.kind == "plan.python_udf")
    subject = dict(real.subject)
    subject["operator"] = "MapInPandas"
    # `_subject` (sparkforge/facts/spark_plan.py) monta o symbol como
    # "(node_id) operator" -- reconstroi aqui em vez de deixar o texto do
    # operador Arrow original parado no campo.
    subject["symbol"] = f"({subject['node_id']}) MapInPandas"
    udf_type = _PYTHON_UDF_OPERATORS["MapInPandas"]
    assert udf_type == "pandas"
    fact = Fact(
        kind="plan.python_udf",
        subject=subject,
        attrs={"operator": "MapInPandas", "udf_type": udf_type},
        provenance=real.provenance,
    )
    regra = next(r for r in load_catalog() if r["id"] == "SF-PLAN-002")
    achados = judge([fact], [regra], {"spark": "3.5.4"})
    assert len(achados) == 1
    assert achados[0].rule_id == "SF-PLAN-002"


def test_knowledge_registra_o_extrator_sob_photon():
    texto = (ROOT / "knowledge" / "databricks" / "runtime-matrix.md").read_text(encoding="utf-8")
    secao = texto.split("## 4.", 1)[1]
    assert "plan.photon" in secao
    assert "databricks.photon.unresolved" in secao
    assert "udf_type" in secao and "arrow" in secao
