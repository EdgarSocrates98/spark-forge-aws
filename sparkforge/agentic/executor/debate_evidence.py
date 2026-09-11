"""Evidencia nova de um debate: REEXTRAIDA pelo executor, nunca aceita do agente.

Decisao 3 do DESIGN do executor de debate. Um lado pode precisar de um fact que
nao esta na uniao do case -- e isso que torna o par decidivel. Aceitar o fact
escrito pelo agente seria aceitar evidencia fabricada: o JSON de um `Fact` e
texto, e texto de agente nao e medida.

O que o lado entrega e um PONTEIRO: `{"extractor": "<nome>", "path": "<relativo a
raiz do case>"}`. O executor confere o nome contra uma allowlist, confina o
caminho a raiz do case, roda o extrator e so entao o fact existe. A mesma
disciplina de `arbitrate` (secao 12.9 do spec): claim ancora em fact derivado de
artefato, e nao em frase.

## O que a reextracao NAO garante

O artefato continua podendo ter sido escrito pelo proprio agente -- um dump de
`collect lakeformation` montado a mao passa pelo extrator igual a um coletado.
O que a reextracao garante e mais estreito, e e o que ela afirma: o fact tem a
forma, o `id` e a procedencia que o extrator produz, e o registro guarda o
`sha1` do artefato lido. Quem audita o debate sabe QUAL arquivo sustentou cada
fact, e pode confere-lo; o que ninguem consegue e citar um fact que nenhum
extrator produziu.

## Por que so extratores `(path, repo_root)`

A allowlist traz os extratores de UM arquivo que ancoram a procedencia relativa
a raiz do case. Ficam de fora, e a razao esta ao lado de cada um:

- `glue_job_run` le um DIRETORIO e pede `job_name` -- outra forma de chamada;
- `cloudwatch`, `cloudwatch_logs` e `parquet_footer` nao recebem `repo_root`, e a
  procedencia sairia com o caminho absoluto da maquina de quem debateu;
- `host_transcript` le transcript do HOST, que e a fala do agente -- justamente o
  que esta porta existe para nao aceitar como medida.

Este modulo nao grava nada sozinho alem de `append_evidence_facts`, e quem o
chama so grava depois de validar a submissao inteira.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
from typing import Any

from sparkforge.case.store import CASE_DIR

# nome publico -> (modulo em `sparkforge.facts`, funcao). O nome e o do verbo
# `sparkforge analyze <nome>` que le o mesmo artefato, para o agente reconhecer o
# que ja usa. Import tardio por `importlib`: carregar os 22 extratores para
# validar um nome custaria o motor inteiro a cada `submit`.
EVIDENCE_EXTRACTORS: dict[str, tuple[str, str]] = {
    "athena-workgroup": ("athena_workgroup", "extract_athena_workgroup_path"),
    "catalog-schema": ("catalog_schema", "extract_catalog_schema_path"),
    "consumers": ("consumers", "extract_consumers_path"),
    "controlm-jobs": ("controlm_jobs", "extract_controlm_jobs_path"),
    "data-quality": ("data_quality", "extract_data_quality_path"),
    "emr-cluster": ("emr_cluster", "extract_emr_cluster_path"),
    "emr-eks": ("emr_eks", "extract_emr_eks_path"),
    "emr-serverless": ("emr_serverless", "extract_emr_serverless_path"),
    "event-log": ("event_log", "extract_event_log_path"),
    "glue-resource-link": ("glue_resource_link", "extract_glue_resource_link_path"),
    "graph": ("graph", "extract_graph_path"),
    "iam-access": ("iam_access", "extract_iam_access_path"),
    "iceberg": ("iceberg_metadata", "extract_iceberg_metadata_path"),
    "lakeformation-grants": ("lakeformation_grants", "extract_lakeformation_path"),
    "migration": ("migration", "extract_migration_path"),
    "plan": ("spark_plan", "extract_plan_path"),
    "pyspark": ("pyspark_ast", "extract_path"),
    "s3-listing": ("s3_listing", "extract_s3_listing_path"),
    "sql": ("sql_literal", "extract_sql_path"),
    "sql-metrics": ("sql_metrics", "extract_sql_metrics_path"),
    "terraform": ("terraform", "extract_terraform_path"),
    "workload": ("workload", "extract_workload_path"),
}

# Recusas nomeadas. Sao constantes porque o chamador as devolve ao host, e o
# host decide o que fazer por NOME -- texto livre nao e contrato.
EXTRACTOR_NOT_ALLOWED = "extractor_not_allowed"
ARTIFACT_OUTSIDE_CASE = "artifact_outside_case"
ARTIFACT_NOT_FOUND = "artifact_not_found"
EXTRACTOR_FAILED = "extractor_failed"
INVALID_ARTIFACT_REF = "invalid_schema"

FACTS_FILE = "facts.jsonl"


class EvidenceRefused(Exception):
    """Recusa nomeada da reextracao. `reason` e o nome; `detail`, o porque."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def extract_evidence(
    case_root: Path | str, artifacts: list[Any]
) -> list[dict[str, Any]]:
    """Roda os extratores pedidos e devolve os registros, SEM gravar nada.

    Args:
        case_root: raiz do case; todo `path` e relativo a ela e confinado nela.
        artifacts: a lista `evidence_artifacts` da submissao.

    Returns:
        Um registro por fact produzido, na ordem dos artefatos e na ordem que o
        extrator devolveu: `{"extractor", "path", "artifact_sha1", "fact"}`.

    Raises:
        EvidenceRefused: na PRIMEIRA recusa. A submissao inteira e recusada, e
            o chamador nao grava nada -- meia evidencia aceita seria pior que
            nenhuma, porque a submissao citaria o que sobrou.
    """
    if not isinstance(artifacts, list):
        raise EvidenceRefused(INVALID_ARTIFACT_REF, "`evidence_artifacts` deve ser lista")

    raiz = os.path.realpath(os.fspath(case_root))
    registros: list[dict[str, Any]] = []
    for indice, artefato in enumerate(artifacts):
        nome, relativo = _ponteiro(artefato, indice)
        funcao = _extrator(nome)
        alvo = _confinado(raiz, relativo)
        try:
            conteudo = Path(alvo).read_bytes()
            facts = funcao(Path(alvo), Path(raiz))
        except Exception as exc:  # o extrator e de terceiro para este modulo
            raise EvidenceRefused(
                EXTRACTOR_FAILED,
                f"`{nome}` falhou sobre `{relativo}`: {type(exc).__name__}: {exc}",
            ) from exc
        sha1 = hashlib.sha1(conteudo, usedforsecurity=False).hexdigest()
        for fact in facts:
            registros.append(
                {
                    "extractor": nome,
                    "path": Path(relativo).as_posix(),
                    "artifact_sha1": sha1,
                    "fact": fact.to_dict(),
                }
            )
    return registros


def read_evidence_facts(debate_dir: Path | str) -> list[dict[str, Any]]:
    """Os registros ja reextraidos neste debate, na ordem em que entraram."""
    arquivo = Path(debate_dir) / FACTS_FILE
    if not arquivo.is_file():
        return []
    registros: list[dict[str, Any]] = []
    with arquivo.open("r", encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if linha:
                registros.append(json.loads(linha))
    return registros


def append_evidence_facts(
    debate_dir: Path | str, registros: list[dict[str, Any]], ja_citaveis: set[str]
) -> list[str]:
    """Acrescenta os registros novos a `facts.jsonl` e devolve os ids gravados.

    Fact cujo `id` ja e citavel -- esta na uniao congelada ou ja foi
    reextraido antes -- nao e regravado. O `id` e content-addressed, e o mesmo
    fact duas vezes e UMA medida (mesma razao de `run._facts_unicos`).
    """
    vistos = set(ja_citaveis)
    novos: list[dict[str, Any]] = []
    for registro in registros:
        fact_id = str((registro.get("fact") or {}).get("id") or "")
        if not fact_id or fact_id in vistos:
            continue
        vistos.add(fact_id)
        novos.append(registro)
    if not novos:
        return []
    arquivo = Path(debate_dir) / FACTS_FILE
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("a", encoding="utf-8") as fh:
        for registro in novos:
            fh.write(json.dumps(registro, ensure_ascii=True, sort_keys=True) + "\n")
    return [str(r["fact"]["id"]) for r in novos]


# --------------------------------------------------------------------------
# Validacao do ponteiro
# --------------------------------------------------------------------------


def _ponteiro(artefato: Any, indice: int) -> tuple[str, str]:
    """`(extractor, path)` de um item, ou recusa por forma."""
    if not isinstance(artefato, dict) or set(artefato) != {"extractor", "path"}:
        raise EvidenceRefused(
            INVALID_ARTIFACT_REF,
            f"evidence_artifacts[{indice}] deve ter exatamente `extractor` e `path`",
        )
    nome, relativo = artefato["extractor"], artefato["path"]
    if not isinstance(nome, str) or not isinstance(relativo, str) or not relativo.strip():
        raise EvidenceRefused(
            INVALID_ARTIFACT_REF,
            f"evidence_artifacts[{indice}]: `extractor` e `path` devem ser texto nao vazio",
        )
    return nome, relativo


def _extrator(nome: str) -> Any:
    """A funcao da allowlist, ou `extractor_not_allowed`.

    O modulo e resolvido so a partir da tabela constante: o nome vindo do
    agente escolhe uma CHAVE, nunca compoe o caminho de import.
    """
    entrada = EVIDENCE_EXTRACTORS.get(nome)
    if entrada is None:
        raise EvidenceRefused(
            EXTRACTOR_NOT_ALLOWED,
            f"`{nome}` nao esta na allowlist: {', '.join(sorted(EVIDENCE_EXTRACTORS))}",
        )
    modulo, funcao = entrada
    return getattr(importlib.import_module(f"sparkforge.facts.{modulo}"), funcao)


def _confinado(raiz: str, relativo: str) -> str:
    """O caminho real do artefato, confinado a raiz do case.

    `realpath` antes do prefixo: `..`, caminho absoluto e link simbolico que
    aponta para fora caem todos na mesma checagem. `commonpath` e nao
    `startswith`, porque `C:\\case2` comeca com `C:\\case` e nao esta dentro dele.

    O diretorio de estado do case (`.sparkforge/`) tambem e recusado: ali mora o
    proprio debate -- submissoes, facts reextraidos, blackboard --, e deixar o
    agente apontar o extrator para esses arquivos seria deixa-lo citar, como
    artefato, o que ele mesmo escreveu.
    """
    alvo = os.path.realpath(os.path.join(raiz, relativo))
    if not _dentro(alvo, raiz) or os.path.normcase(alvo) == os.path.normcase(raiz):
        raise EvidenceRefused(
            ARTIFACT_OUTSIDE_CASE, f"`{relativo}` resolve para fora da raiz do case"
        )
    if _dentro(alvo, os.path.join(raiz, CASE_DIR)):
        raise EvidenceRefused(
            ARTIFACT_OUTSIDE_CASE,
            f"`{relativo}` esta no diretorio de estado `{CASE_DIR}/`, que nao e artefato",
        )
    if not os.path.isfile(alvo):
        raise EvidenceRefused(ARTIFACT_NOT_FOUND, f"`{relativo}` nao existe no case")
    return alvo


def _dentro(caminho: str, base: str) -> bool:
    """`caminho` esta dentro de `base` (ou e ela)? Comparado com `normcase`.

    No Windows `commonpath` compara sem caixa mas devolve a caixa do primeiro
    argumento; comparar o retorno cru com `base` daria falso negativo so por
    `C:` contra `c:`.
    """
    try:
        comum = os.path.commonpath([caminho, base])
    except ValueError:  # drives diferentes no Windows
        return False
    return os.path.normcase(comum) == os.path.normcase(base)
