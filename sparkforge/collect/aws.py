"""Coletores AWS reais: event log (S3), definicao de job (Glue), metricas de
observabilidade (CloudWatch) e metadata tables Iceberg (Athena).

So le. Nenhuma funcao aqui grava em S3, muda estado de um job Glue, ou
executa manutencao de tabela -- `get_object`, `list_objects_v2`,
`get_job`, `get_metric_data` e consultas `SELECT` via Athena, e nada mais.

`boto3` nunca e importado no topo deste modulo (ver `sparkforge.collect.base
require_boto3`): cada coletor so toca `require_boto3()` depois de checar se
o artefato ja esta presente e integro localmente. Isto tem duas
consequencias, as duas intencionais: (1) o nucleo determinístico continua
funcionando sem `boto3` instalado, porque nada aqui e chamado por padrao;
(2) uma segunda coleta do mesmo artefato sem mudanca no lado AWS nao toca a
rede nem exige credenciais -- e um no-op puramente local (offline-first).

`now` e sempre parametro, nunca lido do relogio (mesma convencao do resto do
projeto: `sparkforge.case.store.new_case`, `sparkforge.adapters.cli` etc.).
Isto e o que torna `collected_at == now` (coleta nova) versus
`collected_at != now` (cache hit local, nada foi buscado) uma forma barata
de o chamador (a CLI) saber se a chamada foi um no-op sem um segundo valor
de retorno.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sparkforge.collect.base import (
    ArtifactEntry,
    CollectorUnavailable,
    load_manifest,
    register_artifact,
    require_boto3,
    verify_artifact,
)

# Segundos entre tentativas de poll de uma query Athena ainda em execucao.
# So importa quando a query realmente demora -- um cliente de teste que
# devolve SUCCEEDED na primeira checagem nunca dorme.
_ATHENA_POLL_SECONDS = 1.0

# Nomes exatos de metrica de observabilidade Glue, de
# `knowledge/glue/observability.md`. `glue.driver.bytesWrittten` tem tres
# "t" -- e como a documentacao da AWS escreve, reproduzido aqui sem
# "corrigir": uma query CloudWatch com a grafia certa (duas "t") nao acha
# a metrica.
# Nome da metrica -> Stat correta, conforme knowledge/glue/observability.md.
# `Stat` uniforme e defeito de dado, nao simplificacao: `glue.error.ALL` e
# `glue.succeed.ALL` sao contadores documentados como SUM, e pedir Average deles
# devolve um numero errado com aparencia de certo -- exatamente a classe de
# resultado que este projeto existe para nao produzir. `bytesWrittten` mantem os
# tres `t` porque e como a AWS escreve.
CLOUDWATCH_METRICS: tuple[tuple[str, str], ...] = (
    ("glue.driver.skewness.stage", "Maximum"),
    ("glue.driver.skewness.job", "Maximum"),
    ("glue.driver.workerUtilization", "Average"),
    ("glue.driver.memory.heap.used.percentage", "Maximum"),
    ("glue.driver.memory.total.used.percentage", "Maximum"),
    ("glue.ALL.memory.heap.used.percentage", "Maximum"),
    ("glue.ALL.memory.total.used.percentage", "Maximum"),
    ("glue.driver.disk.used.percentage", "Maximum"),
    ("glue.driver.bytesRead", "Average"),
    ("glue.driver.recordsRead", "Average"),
    ("glue.driver.filesRead", "Average"),
    ("glue.driver.partitionsRead", "Average"),
    ("glue.driver.bytesWrittten", "Average"),
    ("glue.driver.recordsWritten", "Average"),
    ("glue.driver.filesWritten", "Average"),
    ("glue.succeed.ALL", "Sum"),
    ("glue.error.ALL", "Sum"),
)

CLOUDWATCH_METRIC_NAMES: tuple[str, ...] = tuple(n for n, _ in CLOUDWATCH_METRICS)

# As cinco metadata tables do Iceberg que este coletor consulta via Athena.
# `partition_spec`/`sort_order` (ver `sparkforge/facts/iceberg_metadata.py`)
# nao vem de uma metadata table `SELECT *` -- sao metadados estruturais que
# exigiriam `SHOW CREATE TABLE`/API de catalogo, fora do escopo deste
# coletor; o extrator ja trata as duas chaves como opcionais por causa disso.
ICEBERG_METADATA_SECTIONS: tuple[str, ...] = (
    "files",
    "delete_files",
    "snapshots",
    "manifests",
    "partitions",
)


class CollectionFailed(RuntimeError):
    """A chamada AWS se conectou, mas a coleta nao pode ser concluida --
    query Athena terminou em FAILED/CANCELLED, listagem S3 vazia, etc.
    Distinto de `CollectorUnavailable`, que e boto3 ausente ou credenciais
    indisponiveis (a chamada nunca chegou a acontecer)."""


# Caminho relativo esperado de cada tipo de artefato, ancorado em `root`. Uma
# funcao por tipo (em vez de um dict fixo) para que o chamador (a CLI, ao
# montar uma mensagem de erro acionavel quando `boto3` falta) monte o mesmo
# caminho que o coletor vai usar sem duplicar a logica de formatacao.
def event_log_path(job_run_id: str) -> str:
    return f".sparkforge/artifacts/eventlog/{job_run_id}.jsonl"


def glue_job_path(job_name: str) -> str:
    return f".sparkforge/artifacts/glue_job/{job_name}.json"


def cloudwatch_path(job_name: str, job_run_id: str) -> str:
    return f".sparkforge/artifacts/cloudwatch/{job_name}_{job_run_id}.json"


def iceberg_metadata_path(table: str) -> str:
    return f".sparkforge/artifacts/iceberg/{table.replace('.', '_')}.json"


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _offline_hit(root: Path | str, rel_path: str) -> ArtifactEntry | None:
    """Devolve a entrada ja registrada se o artefato esta presente no disco
    E seu sha256 bate com o manifesto -- o caso offline-first, sem tocar em
    boto3 nem em rede. `None` sinaliza "precisa coletar", nao "erro"."""
    entry_dict = next(
        (e for e in load_manifest(root) if e.get("path") == rel_path), None
    )
    if entry_dict is None:
        return None
    result = verify_artifact(entry_dict, root)
    if not (result["present"] and result["hash_matches"]):
        return None
    return ArtifactEntry(
        kind=entry_dict["kind"],
        path=entry_dict["path"],
        sha256=entry_dict["sha256"],
        source=entry_dict["source"],
        collect_command=entry_dict["collect_command"],
        collected_at=entry_dict["collected_at"],
    )


def _write_and_register(
    root: Path | str,
    rel_path: str,
    content: bytes,
    *,
    kind: str,
    source: str,
    collect_command: str,
    now: str,
) -> ArtifactEntry:
    path = Path(root) / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    entry = ArtifactEntry(
        kind=kind,
        path=rel_path,
        sha256=_sha256_bytes(content),
        source=source,
        collect_command=collect_command,
        collected_at=now,
    )
    register_artifact(entry, root)
    return entry


# --------------------------------------------------------------------------- #
# event log (S3)
# --------------------------------------------------------------------------- #


def collect_event_log(
    job_run_id: str, root: Path, *, bucket: str, prefix: str, now: str
) -> ArtifactEntry:
    """Baixa o Spark event log de um job run via `s3.get_object`.

    Glue escreve o event log sob `s3://<bucket>/<prefix>/<job_run_id>/`, e
    pode particiona-lo em mais de um objeto (rollover para runs longos).
    `list_objects_v2` enumera os objetos daquele prefixo, e um `get_object`
    por objeto (ordenados por chave, para saida deterministica) concatena o
    conteudo no `.jsonl` local que `sparkforge.facts.event_log` le.
    """
    rel_path = event_log_path(job_run_id)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("s3")

    key_prefix = f"{prefix.rstrip('/')}/{job_run_id}/"
    listing = client.list_objects_v2(Bucket=bucket, Prefix=key_prefix)
    contents = listing.get("Contents") or []
    if not contents:
        raise CollectionFailed(
            f"nenhum objeto de event log em s3://{bucket}/{key_prefix}. "
            "Confirme --enable-spark-ui e --spark-event-logs-path no job, e que "
            "o job run ja terminou de escrever o log."
        )

    chunks: list[bytes] = []
    for obj in sorted(contents, key=lambda o: o["Key"]):
        body = client.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
        if isinstance(body, str):
            body = body.encode("utf-8")
        chunks.append(body.rstrip(b"\n"))
    content = b"\n".join(chunks) + b"\n"

    return _write_and_register(
        root,
        rel_path,
        content,
        kind="event_log",
        source=f"s3://{bucket}/{key_prefix}",
        collect_command=(
            f"sparkforge collect event-log --job-run {job_run_id} "
            f"--bucket {bucket} --prefix {prefix}"
        ),
        now=now,
    )


# --------------------------------------------------------------------------- #
# definicao do job (Glue)
# --------------------------------------------------------------------------- #


def collect_glue_job(job_name: str, root: Path, *, now: str) -> ArtifactEntry:
    """Baixa a definicao de um job via `glue.get_job` e grava como JSON.

    Isto e o que alimenta analise no formato de `tf.attribute` para o job tal
    como esta *implantado* -- em vez do que o `.tf` fonte declara. Os dois
    podem divergir (alguem mudou `number_of_workers` no console, ou o
    `terraform apply` mais recente nunca rodou), e essa divergencia em si e
    informacao que vale reportar, nao um erro deste coletor.
    """
    rel_path = glue_job_path(job_name)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("glue")
    response = client.get_job(JobName=job_name)
    job = response.get("Job") or {}

    content = json.dumps(job, indent=2, sort_keys=True, default=str, ensure_ascii=False).encode(
        "utf-8"
    )
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="terraform",
        source=f"glue:get_job:{job_name}",
        collect_command=f"sparkforge collect glue-job --job-name {job_name}",
        now=now,
    )


# --------------------------------------------------------------------------- #
# metricas de observabilidade (CloudWatch)
# --------------------------------------------------------------------------- #


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def collect_cloudwatch(
    job_name: str, job_run_id: str, root: Path, *, now: str, start: str, end: str
) -> ArtifactEntry:
    """Baixa as metricas de observabilidade Glue via `cloudwatch.get_metric_data`.

    `start`/`end` sao ISO 8601 fornecidos pelo chamador -- este modulo nunca
    le o relogio. Consulta exatamente os nomes de `CLOUDWATCH_METRICS`
    (extraidos de `knowledge/glue/observability.md`), dimensionados por
    `JobName`+`JobRunId`. Requer `glueContext` inicializado no job e
    `--enable-observability-metrics=true`; se nao, o CloudWatch simplesmente
    nao tem essas series -- `get_metric_data` devolve resultados vazios, nao
    um erro, e este coletor grava o que veio de volta sem tentar adivinhar.
    """
    rel_path = cloudwatch_path(job_name, job_run_id)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("cloudwatch")

    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)
    dimensions = [
        {"Name": "JobName", "Value": job_name},
        {"Name": "JobRunId", "Value": job_run_id},
    ]
    queries = [
        {
            "Id": f"m{index}",
            "MetricStat": {
                "Metric": {"Namespace": "Glue", "MetricName": metric, "Dimensions": dimensions},
                "Period": 30,
                "Stat": stat,
            },
            "Label": metric,
            "ReturnData": True,
        }
        for index, (metric, stat) in enumerate(CLOUDWATCH_METRICS)
    ]

    response = client.get_metric_data(
        MetricDataQueries=queries, StartTime=start_dt, EndTime=end_dt
    )
    payload = {
        "job_name": job_name,
        "job_run_id": job_run_id,
        "start": start,
        "end": end,
        "metric_data_results": response.get("MetricDataResults") or [],
    }
    content = json.dumps(payload, indent=2, sort_keys=True, default=str, ensure_ascii=False).encode(
        "utf-8"
    )
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="cloudwatch",
        source=f"cloudwatch:get_metric_data:{job_name}/{job_run_id}",
        collect_command=(
            f"sparkforge collect cloudwatch --job-name {job_name} --job-run {job_run_id} "
            f"--start {start} --end {end}"
        ),
        now=now,
    )


# --------------------------------------------------------------------------- #
# metadata tables Iceberg (Athena)
# --------------------------------------------------------------------------- #


def _split_table(table: str) -> tuple[str, str]:
    database, _, name = table.partition(".")
    return database, name


def _coerce_athena_value(value: str | None) -> Any:
    """Athena devolve toda celula como string (`VarCharValue`). As metadata
    tables do Iceberg tem colunas numericas (`file_size_in_bytes`,
    `record_count`, `length`, `added_data_files_count`, ...) que
    `sparkforge.facts.iceberg_metadata` so agrega quando o tipo Python e
    `int`/`float` -- uma string nunca passa no `isinstance` de la, e a secao
    inteira seria silenciosamente ignorada. Coagir aqui e o que faz o
    artefato coletado ser de fato legivel pelo extrator, nao so presente."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if value in ("true", "false"):
        return value == "true"
    return value


def _athena_rows_to_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Primeira linha e o cabecalho (nome de coluna); as demais sao dados.
    Uma metadata table sem linhas (`rows == []`, nem cabecalho) vira `[]`."""
    if not rows:
        return []
    header = [cell.get("VarCharValue", "") for cell in rows[0].get("Data", [])]
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        cells = row.get("Data", [])
        record = {
            header[i]: _coerce_athena_value(cell.get("VarCharValue"))
            for i, cell in enumerate(cells)
            if i < len(header)
        }
        records.append(record)
    return records


def _run_athena_query(
    client: Any, query: str, workgroup: str, output_location: str
) -> list[dict[str, Any]]:
    start = client.start_query_execution(
        QueryString=query,
        WorkGroup=workgroup,
        ResultConfiguration={"OutputLocation": output_location},
    )
    execution_id = start["QueryExecutionId"]

    while True:
        status = client.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in ("FAILED", "CANCELLED"):
            reason = status["QueryExecution"]["Status"].get("StateChangeReason", "")
            raise CollectionFailed(
                f"consulta Athena {execution_id} terminou em {state}: {reason}\n"
                f"  query: {query}"
            )
        time.sleep(_ATHENA_POLL_SECONDS)

    results = client.get_query_results(QueryExecutionId=execution_id)
    return results.get("ResultSet", {}).get("Rows") or []


def collect_iceberg_metadata(
    table: str, root: Path, *, workgroup: str, output_location: str, now: str
) -> ArtifactEntry:
    """Consulta as cinco metadata tables Iceberg de `table` via Athena e
    monta o JSON no formato que `sparkforge.facts.iceberg_metadata` le.

    `table` e `db.tabela`. Cada secao vira `SELECT * FROM "db"."tabela$secao"`
    -- a sintaxe de metadata table do Athena/Iceberg -- e a resposta e
    convertida para o shape documentado no topo de
    `sparkforge/facts/iceberg_metadata.py`. Uma secao que a query devolve
    vazia vira lista vazia no JSON, nunca uma chave ausente: o extrator
    distingue "coletado e vazio" de "nao coletado" pela presenca da chave.
    """
    rel_path = iceberg_metadata_path(table)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("athena")
    database, name = _split_table(table)

    payload: dict[str, Any] = {"table": table}
    for section in ICEBERG_METADATA_SECTIONS:
        # `database`/`name` vem do argumento `table` do chamador (CLI local,
        # nao entrada remota), e `section` e um dos cinco valores fixos de
        # `ICEBERG_METADATA_SECTIONS` -- nao ha parametro de query Athena
        # para nomes de tabela/metadata table, so para valores de `WHERE`,
        # que este SELECT nem usa.
        query = f'SELECT * FROM "{database}"."{name}${section}"'  # noqa: S608
        rows = _run_athena_query(client, query, workgroup, output_location)
        payload[section] = _athena_rows_to_records(rows)

    content = json.dumps(payload, indent=2, sort_keys=True, default=str, ensure_ascii=False).encode(
        "utf-8"
    )
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="iceberg_metadata",
        source=f"athena:{table}",
        collect_command=(
            f"sparkforge collect iceberg-metadata --table {table} "
            f"--workgroup {workgroup} --output-location {output_location}"
        ),
        now=now,
    )


__all__ = [
    "CLOUDWATCH_METRICS",
    "CLOUDWATCH_METRIC_NAMES",
    "ICEBERG_METADATA_SECTIONS",
    "CollectionFailed",
    "CollectorUnavailable",
    "cloudwatch_path",
    "collect_cloudwatch",
    "collect_event_log",
    "collect_glue_job",
    "collect_iceberg_metadata",
    "event_log_path",
    "glue_job_path",
    "iceberg_metadata_path",
]
