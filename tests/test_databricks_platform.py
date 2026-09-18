"""Databricks como plataforma declarada, com fronteira onde o significado muda."""
import argparse
import inspect
import json
from pathlib import Path

from sparkforge.adapters import _core, cli, tools
from sparkforge.adapters._core import build_runtime, runtime_sources_from_facts
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.facts.spark_plan import extract_plan_path
from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog
from sparkforge.tuning.spark_conf import build_conf_advice

ROOT = Path(__file__).resolve().parents[1]
PLANO = ROOT / "fixtures" / "plan" / "cartesian_join" / "input"

_CHAVE_VERSAO = "spark.databricks.clusterUsageTags.sparkVersion"


def _conf(chave: str, valor: str) -> Fact:
    return Fact(
        kind="spark.conf_effective",
        subject={"type": "job_run", "symbol": chave},
        attrs={"key": chave, "value": valor, "source_event": "SparkListenerEnvironmentUpdate"},
        provenance={"extractor": "event_log@0.1.0"},
    )


def test_flag_declara_plataforma_e_deriva_spark():
    context, facts = build_runtime(databricks="15.4.x-scala2.12")
    assert context.databricks == "15.4"
    assert context.spark == "3.5.0"
    assert context.detected_from == ["cli"]
    assert context.to_dict()["databricks"] == "15.4"
    plataforma = next(f for f in facts if f.kind == "env.platform")
    assert plataforma.attrs["resolved"] == "databricks"
    divergente, _ = detect_runtime(
        {"cli": {"databricks_runtime": "15.4.x-scala2.12"}, "event_log": {"spark_version": "3.5.2"}}
    )
    assert "cli:matrix=3.5.0" in " ".join(divergente.divergences)
    maior, _ = build_runtime(databricks="18.0.x-scala2.13")
    assert (maior.databricks, maior.spark) == ("18.0", "4.1.0")
    fora, _ = build_runtime(databricks="9.1.x-scala2.12")
    assert (fora.databricks, fora.spark) == ("9.1", "")


def test_event_log_declara_plataforma_databricks():
    fatos = [_conf(_CHAVE_VERSAO, "15.4.x-scala2.12")]
    assert runtime_sources_from_facts(fatos) == {
        "event_log": {"databricks_runtime": "15.4.x-scala2.12"}
    }
    context, facts = build_runtime(facts=fatos)
    assert (context.databricks, context.spark) == ("15.4", "3.5.0")
    plataforma = next(f for f in facts if f.kind == "env.platform")
    assert plataforma.attrs["origins"] == {"databricks": ["event_log"]}
    assert runtime_sources_from_facts([_conf("spark.app.name", "x")]) == {}


def test_photon_recusa_regra_de_plano():
    fatos = extract_plan_path(PLANO / "plan.txt", repo_root=PLANO)
    base = {"databricks": "15.4", "spark": "3.5.0"}
    ligado, pulados = judge(fatos, load_catalog(), {**base, "photon": "on"}, return_skipped=True)
    desligado = judge(fatos, load_catalog(), {**base, "photon": "off"})
    sem_databricks = judge(fatos, load_catalog(), {"spark": "3.5.0", "photon": "on"})
    assert "SF-PLAN-003" in {f.rule_id for f in desligado}
    assert "SF-PLAN-003" in {f.rule_id for f in sem_databricks}
    assert "SF-PLAN-003" not in {f.rule_id for f in ligado}
    assert {"rule_id": "SF-PLAN-003", "reason": "databricks.photon.unresolved"} in pulados

    context, facts = build_runtime(databricks="15.4")
    assert context.photon == ""
    assert next(f for f in facts if f.kind == "databricks.photon").attrs["state"] == "undeclared"
    assert "SF-ENV-006" in {f.rule_id for f in judge(facts, load_catalog(), context.to_dict())}

    context_on, facts_on = build_runtime(databricks="15.4", photon="on")
    assert context_on.photon == "on"
    assert next(f for f in facts_on if f.kind == "databricks.photon").attrs["state"] == "on"
    achados_on = judge(facts_on, load_catalog(), context_on.to_dict())
    assert "SF-ENV-006" not in {f.rule_id for f in achados_on}

    _, facts_glue = build_runtime(glue="5.0", photon="on")
    assert not any(f.kind == "databricks.photon" for f in facts_glue)


def test_shuffle_partitions_auto_recusado():
    fatos = [
        _conf("spark.sql.shuffle.partitions", "auto"),
        Fact(
            kind="spark.stage.shuffle",
            subject={"type": "stage", "symbol": "1"},
            measures={"write_bytes": 10 * 1024**3},
            provenance={"extractor": "event_log@0.1.0"},
        ),
    ]
    conselho = build_conf_advice(fatos, runtime={"databricks": "15.4", "spark": "3.5.0"})
    recusa = next(
        r for r in conselho["refused"] if r["property"] == "spark.sql.shuffle.partitions"
    )
    assert recusa["reason"] == "shuffle_partitions_auto"
    assert all(p["key"] != "spark.sql.shuffle.partitions" for p in conselho["properties"])

    numerico = build_conf_advice(
        [_conf("spark.sql.shuffle.partitions", "400"), fatos[1]],
        runtime={"databricks": "15.4", "spark": "3.5.0"},
    )
    assert any(p["key"] == "spark.sql.shuffle.partitions" for p in numerico["properties"])


def _subparsers(parser):
    for acao in parser._actions:
        if isinstance(acao, argparse._SubParsersAction):
            for nome, sub in acao.choices.items():
                yield nome, sub
                yield from _subparsers(sub)


def test_flags_seguem_o_emr(capsys):
    faltando = []
    for nome, sub in _subparsers(cli.build_parser()):
        opcoes = {o for acao in sub._actions for o in acao.option_strings}
        if "--emr" in opcoes and not {"--databricks", "--photon"} <= opcoes:
            faltando.append(("cli", nome))
    for nome, spec in tools.TOOLS.items():
        propriedades = spec.get("inputSchema", {}).get("properties", {})
        if "emr" in propriedades and not {"databricks", "photon"} <= set(propriedades):
            faltando.append(("mcp", nome))
    for nome, funcao in inspect.getmembers(_core, inspect.isfunction):
        if nome.startswith("_"):
            continue
        parametros = inspect.signature(funcao).parameters
        if "emr" in parametros and not {"databricks", "photon"} <= set(parametros):
            faltando.append(("core", nome))
    assert faltando == []

    # `--photon` recusa valor fora de on/off em TODO verbo, inclusive nos laços
    # genericos de proof, simulate e scan: valor invalido nao pode virar "nao
    # declarado" em silencio.
    sem_choices = [
        nome
        for nome, sub in _subparsers(cli.build_parser())
        for acao in sub._actions
        if "--photon" in acao.option_strings and tuple(acao.choices or ()) != ("on", "off")
    ]
    assert sem_choices == []

    assert cli.main(["runtime", "detect", "--databricks", "15.4", "--photon", "on"]) == 0
    saida = json.loads(capsys.readouterr().out)
    assert (saida["databricks"], saida["spark"], saida["photon"]) == ("15.4", "3.5.0", "on")
    mcp = tools.call_tool("sparkforge_runtime_detect", {"databricks": "15.4", "photon": "off"})
    assert (mcp["databricks"], mcp["photon"]) == ("15.4", "off")


def test_divergencia_spark_registrada():
    context, facts = detect_runtime(
        {"event_log": {"spark_version": "3.5.2"}, "cli": {"databricks_runtime": "15.4"}}
    )
    assert context.databricks == "15.4"
    assert context.spark == "3.5.2"
    assert any(texto.startswith("spark:") for texto in context.divergences)
    sinal = next(
        f for f in facts if f.kind == "env.runtime_signal" and f.attrs["component"] == "spark"
    )
    assert sinal.measures["distinct_versions"] == 2
    golden = ROOT / "fixtures" / "runtime" / "databricks_divergent_spark" / "expected"
    disparadas = {f["rule_id"] for f in json.loads((golden / "findings.json").read_text(encoding="utf-8"))}
    assert "SF-ENV-001" in disparadas
