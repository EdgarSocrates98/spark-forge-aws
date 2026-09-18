"""Regra sem escopo que um job Databricks alcanca nao remedia so para AWS.

O conjunto e recalculado dos EMITTED_KINDS dos extratores que um job Spark no
Databricks produz, nunca de uma lista de regras escrita a mao.
"""
import importlib

from sparkforge.rules.loader import load_catalog

EXTRATORES = (
    "event_log", "spark_plan", "sql_metrics", "pyspark_ast", "parquet_footer",
    "timeout_diagnosis", "bridge", "exception", "call_graph", "utilization",
    "workload", "runtime_detect",
)
TERMOS_AWS = ("Glue", "DPU", "G.1X", "G.2X", "EMR", "Lake Formation", "Athena", "DynamicFrame")
CAMPOS = ("proposed_change", "rollback", "validation", "explanation", "expected_effect", "risks", "tradeoffs")
EXCECOES = {
    "SF-PQ-002": (
        "o passo com DynamicFrame e condicional a leitura via DynamicFrame, que so "
        "existe no Glue; os demais passos da regra sao neutros"
    ),
}


def _kinds() -> set[str]:
    kinds: set[str] = set()
    for nome in EXTRATORES:
        kinds |= set(importlib.import_module(f"sparkforge.facts.{nome}").EMITTED_KINDS)
    return kinds


def _texto(regra: dict) -> str:
    return " ".join(str(regra.get(campo, "")) for campo in CAMPOS)


def _alcancaveis() -> list[dict]:
    kinds = _kinds()
    saida = []
    for regra in load_catalog():
        if regra.get("runtime_scope") or regra.get("executable") is False:
            continue
        exigidos = set(regra.get("requires_facts") or [])
        if exigidos and exigidos <= kinds:
            saida.append(regra)
    return saida


def test_regra_sem_escopo_nao_remedia_com_termo_aws():
    violadoras = {}
    for regra in _alcancaveis():
        texto = _texto(regra)
        termos = [t for t in TERMOS_AWS if t in texto]
        if termos and "Databricks" not in texto and regra["id"] not in EXCECOES:
            violadoras[regra["id"]] = termos
    assert violadoras == {}
    mortas = set(EXCECOES) - {r["id"] for r in _alcancaveis() if any(t in _texto(r) for t in TERMOS_AWS)}
    assert mortas == set()
