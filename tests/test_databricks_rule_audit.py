"""Regra sem escopo que um job Databricks alcanca nao remedia so para AWS.

O conjunto e recalculado dos EMITTED_KINDS de TODO extrator de `sparkforge/facts/`,
menos uma lista NOMEADA de extratores que so leem artefato de AWS -- nunca de uma
lista de inclusao, que envelhece calada quando nasce extrator generico novo, e nunca
de uma lista de regras escrita a mao.
"""
import importlib
import pkgutil
import re

import sparkforge.facts
from sparkforge.rules.loader import load_catalog

# Extrator cujo artefato so existe na AWS. Um job Databricks nunca produz os kinds
# dele, entao a regra que os exige nao alcanca o usuario Databricks. Na duvida, o
# extrator NAO entra aqui.
SO_AWS = {
    "terraform": "le recurso `aws_glue_job` (e irmaos `aws_*`) do Terraform",
    "glue_job_run": "le a resposta de `get_job_runs` da API do Glue",
    "run_cost": "custo sobre `dpu_seconds` de `glue.job_run`, a API do Glue",
    "catalog_schema": "le dump de `GetTables`/`GetTable` do Glue Data Catalog",
    "glue_resource_link": "le resource link do Glue Data Catalog",
    "emr_cluster": "le `describe-cluster` do EMR on EC2",
    "emr_serverless": "le `get-application` do EMR Serverless",
    "emr_eks": "le job run e cluster virtual do EMR on EKS (`emr-containers`)",
    "athena_workgroup": "le `get_work_group` do Athena",
    "iam_access": "le simulacao de politica do IAM",
    "lakeformation": "le o modelo de acesso do Lake Formation declarado no job",
    "lakeformation_grants": "le grants e settings do Lake Formation",
    "cloudwatch": "le `get_metric_data` do CloudWatch (`glue.metric`)",
    "cloudwatch_logs": "le `filter_log_events` do CloudWatch Logs",
    "utilization": (
        "deriva de `glue.metric` (seu `SOURCE_KINDS`), a metrica do Glue no CloudWatch; "
        "sem ela o `fuse` nem deriva"
    ),
}
# Kind de extrator generico que so nasce de fonte AWS: o extrator e generico, mas
# este kind dele so sai cruzando com um fact de extrator de `SO_AWS`.
KINDS_SO_DE_FONTE_AWS = {
    "sql.projection.enriched": (
        "`fusion` so o emite cruzando `sql.projection` com `catalog.table_schema`, "
        "do Glue Data Catalog (`_catalog_lookup`)"
    ),
    "iceberg.library_conflict": (
        "`fusion` so compara contra o Iceberg embarcado derivado do `glue_version` "
        "de `tf.attribute`, do Terraform (`_iceberg_embarcado`)"
    ),
}
# Por palavra, entao `GlueContext` precisa de termo proprio: "Glue" nao casa dentro dele.
TERMOS_AWS = (
    "Glue", "GlueContext", "DPU", "G.1X", "G.2X", "EMR", "Lake Formation", "Athena",
    "DynamicFrame",
)
CAMPOS = ("proposed_change", "rollback", "validation", "explanation", "expected_effect", "risks", "tradeoffs")
EXCECOES = {
    "SF-PQ-002": (
        "o passo com DynamicFrame e condicional a leitura via DynamicFrame, que so "
        "existe no Glue; os demais passos da regra sao neutros"
    ),
}


def _padrao(termo: str) -> re.Pattern[str]:
    # Sem diferenciar caixa e por palavra: `glue.driver.*` casa "Glue", porque o
    # ponto conta como fronteira, e `glue_version` nao casa, porque `_` nao conta.
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(termo) + r"(?![A-Za-z0-9_])", re.IGNORECASE)


_PADROES = {termo: _padrao(termo) for termo in TERMOS_AWS}
_DATABRICKS = _padrao("Databricks")


def _extratores() -> list[str]:
    nomes = []
    for modulo in pkgutil.iter_modules(sparkforge.facts.__path__):
        if hasattr(importlib.import_module(f"sparkforge.facts.{modulo.name}"), "EMITTED_KINDS"):
            nomes.append(modulo.name)
    return sorted(nomes)


def _kinds() -> set[str]:
    kinds: set[str] = set()
    for nome in _extratores():
        if nome in SO_AWS:
            continue
        kinds |= set(importlib.import_module(f"sparkforge.facts.{nome}").EMITTED_KINDS)
    return kinds - set(KINDS_SO_DE_FONTE_AWS)


def _texto(regra: dict) -> str:
    return " ".join(str(regra.get(campo, "")) for campo in CAMPOS)


def _termos(texto: str) -> list[str]:
    return [termo for termo, padrao in _PADROES.items() if padrao.search(texto)]


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


def test_exclusao_so_nomeia_extrator_e_kind_que_existem():
    assert set(SO_AWS) - set(_extratores()) == set()
    assert all(motivo.strip() for motivo in SO_AWS.values())
    emitidos = set().union(
        *(importlib.import_module(f"sparkforge.facts.{n}").EMITTED_KINDS for n in _extratores())
    )
    assert set(KINDS_SO_DE_FONTE_AWS) - emitidos == set()
    assert all(motivo.strip() for motivo in KINDS_SO_DE_FONTE_AWS.values())


def test_regra_sem_escopo_nao_remedia_com_termo_aws():
    violadoras = {}
    for regra in _alcancaveis():
        texto = _texto(regra)
        termos = _termos(texto)
        if termos and not _DATABRICKS.search(texto) and regra["id"] not in EXCECOES:
            violadoras[regra["id"]] = termos
    assert violadoras == {}
    mortas = set(EXCECOES) - {r["id"] for r in _alcancaveis() if _termos(_texto(r))}
    assert mortas == set()
