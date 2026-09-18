"""Databricks como plataforma declarada, com fronteira onde o significado muda."""
import argparse
import inspect
import json
from pathlib import Path

import yaml

from sparkforge.adapters import _core, cli, tools
from sparkforge.adapters._core import build_runtime, runtime_sources_from_facts
from sparkforge.adapters.mcp_envelope import envelope_da_chamada
from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.facts.spark_plan import extract_plan_path
from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog
from sparkforge.tuning.spark_conf import build_conf_advice

ROOT = Path(__file__).resolve().parents[1]
PLANO = ROOT / "fixtures" / "plan" / "cartesian_join" / "input"
EVENTLOG = ROOT / "fixtures" / "eventlog"

_CHAVE_VERSAO = "spark.databricks.clusterUsageTags.sparkVersion"


def _achados(caso: str) -> set[tuple]:
    entrada = EVENTLOG / caso / "input"
    fatos = []
    for jsonl in sorted(entrada.glob("*.jsonl")):
        fatos.extend(extract_event_log_path(jsonl, repo_root=entrada))
    meta = yaml.safe_load((EVENTLOG / caso / "meta.yaml").read_text(encoding="utf-8"))
    return {
        (f.rule_id, f.severity, repr(sorted(f.subject.items())))
        for f in judge(fatos, load_catalog(), meta["runtime"])
    }


def test_fixture_pareada_mesmos_findings_neutros():
    glue = _achados("skewed_stage")
    databricks = _achados("databricks_skewed_stage")
    assert glue
    assert databricks == glue


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


def test_rotulo_18_0_e_a_mesma_identidade_de_18():
    # A matriz escreve `18` onde a API escreve `18.0.x-...`: as duas grafias
    # resolvem a mesma linha e nao podem contar como dois runtimes.
    context, _ = detect_runtime(
        {
            "cli": {"databricks_runtime": "18"},
            "event_log": {"databricks_runtime": "18.0.x-scala2.13"},
        }
    )
    assert not [texto for texto in context.divergences if texto.startswith("databricks:")]


def test_photon_sem_databricks_vira_divergencia():
    context, _ = build_runtime(glue="5.0", photon="on")
    assert context.photon == ""
    photon = [texto for texto in context.divergences if texto.startswith("photon:")]
    assert len(photon) == 1
    assert "databricks" in photon[0]


def test_photon_nao_cala_regra_de_udf_python():
    # A fonte do Photon diz que UDF faz fallback para o Spark: o no de UDF Python
    # e o que roda, e a regra que o procura continua julgando sob Photon.
    entrada = ROOT / "fixtures" / "plan" / "python_udf_in_plan" / "input"
    fatos = extract_plan_path(entrada / "plan.txt", repo_root=entrada)
    runtime = {"databricks": "15.4", "spark": "3.5.0", "photon": "on"}
    achados, pulados = judge(fatos, load_catalog(), runtime, return_skipped=True)
    assert {"SF-PLAN-001", "SF-PLAN-002"} <= {f.rule_id for f in achados}
    recusadas = {p["rule_id"] for p in pulados if p["reason"] == "databricks.photon.unresolved"}
    assert recusadas.isdisjoint({"SF-PLAN-001", "SF-PLAN-002"})
    assert "SF-PLAN-003" in recusadas


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


def test_tune_pelo_mcp_aceita_a_recusa_auto(tmp_path):
    # O fio MCP valida a saida contra o outputSchema (`envelope_da_chamada`, o mesmo
    # caminho de `adapters/mcp.py`): uma recusa fora do enum de `refused[].reason`
    # vira erro no fio, e o verbo passa na CLI mas falha no MCP.
    # `sparkforge_tune` nao aceita `databricks` na entrada (nem `emr`, D6): o runtime
    # sai dos facts, e a recusa `auto` nao depende dele.
    fatos = [
        _conf("spark.sql.shuffle.partitions", "auto"),
        Fact(
            kind="spark.stage.shuffle",
            subject={"type": "stage", "symbol": "1"},
            measures={"write_bytes": 10 * 1024**3},
            provenance={"extractor": "event_log@0.1.0"},
        ),
    ]
    arquivo = tmp_path / "facts.json"
    arquivo.write_text(json.dumps([f.to_dict() for f in fatos]), encoding="utf-8")
    envelope = envelope_da_chamada(
        "sparkforge_tune", {"facts_path": str(arquivo)}, tools.TOOLS, "stdio", tools.call_tool
    )
    assert not envelope.is_error, envelope.text
    assert "shuffle_partitions_auto" in {r["reason"] for r in envelope.structured["refused"]}


def _regras_do_judge(capsys, arquivo: Path, *flags: str) -> set[str]:
    assert cli.main(["judge", "--facts", str(arquivo), *flags]) == 0
    return {item["rule_id"] for item in json.loads(capsys.readouterr().out)["items"]}


def test_judge_em_producao_julga_facts_de_ambiente(tmp_path, capsys):
    # Os facts de `build_runtime` (`env.platform`, `env.runtime_signal`,
    # `databricks.photon`) nao estao no arquivo: sao da deteccao. Um verbo que
    # julga e os descarta deixa SF-ENV-001, 004, 005 e 006 so em fixture.
    arquivo = tmp_path / "facts.json"
    arquivo.write_text(json.dumps([_conf("spark.app.name", "x").to_dict()]), encoding="utf-8")
    assert "SF-ENV-006" in _regras_do_judge(capsys, arquivo, "--databricks", "15.4")
    declarado = _regras_do_judge(capsys, arquivo, "--databricks", "15.4", "--photon", "off")
    assert "SF-ENV-006" not in declarado


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


def test_readme_declara_databricks():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "--databricks" in readme
    assert "knowledge/databricks/runtime-matrix.md" in readme
    status = (ROOT / "docs" / "superpowers" / "STATUS.md").read_text(encoding="utf-8")
    assert "DATABRICKS_SPARK" in status
