"""Extrator do historico de runs Glue em Facts.

Le o diretorio de artefatos `glue_job_run` -- um JSON por run terminal, escrito
por `sparkforge.collect.aws.collect_glue_job_runs` -- e emite o fact por run,
a distribuicao por capacidade x estado terminal, a contagem de desfecho por
capacidade e a correlacao com os facts de CloudWatch ja coletados, casada por
`job_run_id`. Correlacao e opcional (`cloudwatch_dir=None`): sem ela, os facts
de distribuicao saem completos e a correlacao inteira vai para `unresolved`.

O QUE ESTE MODULO RECUSA. Nao emite custo em dinheiro: `facts/pricing.py`
recusa deliberadamente combinar preco com regiao `UNQUALIFIED`, e furar essa
recusa aqui produziria um numero de custo que fonte nenhuma publica. Nao
classifica mensagem de erro por heuristica -- classificar e juizo, e fact nao
julga. E nao carrega a `ErrorMessage` para dentro do fact: ela pode trazer nome
de tabela, caminho de S3 ou trecho de dado.

Puro e deterministico: nunca aplica limiar, nunca toca a rede.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sparkforge.facts.cloudwatch import extract_cloudwatch_path
from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "glue_job_run@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "glue.job_run",
        "glue.job_run.distribution",
        "glue.job_run.outcome",
        "glue.job_run.unresolved",
        "glue.job_run.analyzed",
    }
)

# DPU por worker type, de `knowledge/glue/workers-and-capacity.md` linhas 10-13
# (fonte AWS, retrieved 2026-07-29). Worker fora desta tabela NAO recebe DPU
# derivado: inventar o fator produziria um numero com aparencia de medido.
DPU_BY_WORKER_TYPE: dict[str, int] = {
    "G.1X": 1,
    "G.2X": 2,
    "G.4X": 4,
    "G.8X": 8,
}

_DPU_FORMULA = "number_of_workers * DPU(worker_type) * execution_time_s"
_DPU_SOURCE_DOC = "knowledge/glue/workers-and-capacity.md:79"


def _capacity_symbol(
    job_name: str,
    glue_version: str,
    worker_type: str,
    workers: Any,
    autoscaling: bool,
    state: str | None = None,
) -> str:
    """Assinatura estavel e legivel de um grupo de capacidade, para `subject.symbol`.

    `glue.job_run.distribution` e `glue.job_run.outcome` agregam VARIOS runs
    sob um unico fact; nenhum `job_run_id` isolado os identifica. `subject.type`
    continua `"job_run"` mesmo assim -- mesmo precedente de
    `spark.job.spill_summary` em `sparkforge/facts/event_log.py:646`, que
    agrega o job inteiro sob `type: "job_run"` porque o enum fechado do schema
    (`sparkforge/findings/schemas/fact.schema.json`) nao tem um tipo "grupo"
    proprio, e o run e a entidade mais proxima do que o grupo realmente e.

    Serializado via `json.dumps` de uma lista posicional, e nao por
    f-string concatenada: e injetivo por construcao (cada campo entra
    delimitado por aspas e virgula do proprio JSON), entao dois grupos
    diferentes nunca colidem no mesmo simbolo -- nem quando um campo poderia,
    em tese, conter o separador. `state=None` (outcome, que atravessa todos os
    estados) e `state="FAILED"` (distribution) produzem listas de tamanho
    diferente, o que ja as separa.
    """
    campos: list[Any] = [job_name, glue_version, worker_type, workers, autoscaling]
    if state is not None:
        campos.append(state)
    return json.dumps(campos, separators=(",", ":"))


def _nearest_rank(sorted_values: list[float], pct: int) -> float:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n).

    Mesma formula de `event_log._nearest_rank` e `iceberg_metadata._nearest_rank`,
    reescrita aqui em vez de importada pela razao ja registrada por escrito em
    `iceberg_metadata.py:128`: os extratores sao modulos independentes por
    desenho. O que garante que as tres continuam iguais e teste, nao import.
    """
    n = len(sorted_values)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return sorted_values[rank - 1]


def _is_autoscaling(run: dict[str, Any]) -> bool:
    argumentos = run.get("Arguments") or {}
    return str(argumentos.get("--enable-auto-scaling", "")).lower() == "true"


def _capacity_subject(job_name: str, run: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_name": job_name,
        "glue_version": run.get("GlueVersion") or "",
        "worker_type": run.get("WorkerType") or "",
        "number_of_workers": run.get("NumberOfWorkers"),
        "autoscaling": _is_autoscaling(run),
    }


def _unresolved(
    job_name: str, run_id: str, reason: str, detail: str, collect_command: str = ""
) -> Fact:
    """Lacuna com nome, razao e -- quando existe -- o comando que a resolve.

    `Fact` e `@dataclass(frozen=True)`: os atributos entram na construcao, nunca
    por mutacao depois.
    """
    attrs: dict[str, Any] = {"reason": reason, "detail": detail}
    if collect_command:
        attrs["collect_command"] = collect_command
    return Fact(
        kind="glue.job_run.unresolved",
        subject={
            "job_name": job_name,
            "job_run_id": run_id,
            "type": "job_run",
            "symbol": run_id,
        },
        attrs=attrs,
        provenance={"extractor": EXTRACTOR_ID},
    )


def _dpu_seconds(
    job_name: str, run_id: str, run: dict[str, Any]
) -> tuple[float | None, str | None, dict[str, Any], Fact | None]:
    """Devolve (valor, dpu_source, provenance extra, fact de recusa)."""
    observed = run.get("DPUSeconds")
    if observed is not None:
        return float(observed), "observed", {"dpu_field": "DPUSeconds"}, None

    if _is_autoscaling(run):
        return (
            None,
            None,
            {},
            _unresolved(
                job_name,
                run_id,
                "dpu_unobservable_under_autoscaling",
                "Run com Auto Scaling e sem DPUSeconds na resposta da API. A capacidade "
                "alocada variou durante a execucao e number_of_workers e apenas o teto: "
                "multiplica-lo pela duracao produziria um numero superestimado com "
                "aparencia de medido.",
            ),
        )

    worker_type = run.get("WorkerType") or ""
    dpu = DPU_BY_WORKER_TYPE.get(worker_type)
    workers = run.get("NumberOfWorkers")
    duration = run.get("ExecutionTime")
    if dpu is None:
        return (
            None,
            None,
            {},
            _unresolved(
                job_name,
                run_id,
                "unknown_worker_type",
                f"WorkerType {worker_type!r} fora de {sorted(DPU_BY_WORKER_TYPE)}. O fator "
                f"DPU vem de {_DPU_SOURCE_DOC}; inventa-lo produziria numero com aparencia "
                f"de medido.",
            ),
        )
    if not isinstance(workers, int) or not isinstance(duration, (int, float)):
        return (
            None,
            None,
            {},
            _unresolved(
                job_name,
                run_id,
                "incomplete_capacity_fields",
                "NumberOfWorkers ou ExecutionTime ausentes na resposta da API; sem os dois "
                "a derivacao de DPU nao e possivel.",
            ),
        )
    return (
        float(workers * dpu * duration),
        "derived",
        {"formula": _DPU_FORMULA, "formula_source": _DPU_SOURCE_DOC, "dpu_per_worker": dpu},
        None,
    )


def _run_fact(job_name: str, run: dict[str, Any], path: str) -> tuple[Fact, list[Fact]]:
    run_id = run.get("Id") or ""
    extras: list[Fact] = []

    value, dpu_source, dpu_provenance, refusal = _dpu_seconds(job_name, run_id, run)
    if refusal is not None:
        extras.append(refusal)

    measures: dict[str, Any] = {}
    for chave, campo in (
        ("execution_time_s", "ExecutionTime"),
        ("number_of_workers", "NumberOfWorkers"),
        ("timeout_min", "Timeout"),
    ):
        if run.get(campo) is not None:
            measures[chave] = run[campo]
    if value is not None:
        measures["dpu_seconds"] = value

    attrs: dict[str, Any] = {
        "state": run.get("JobRunState") or "",
        "worker_type": run.get("WorkerType") or "",
        "glue_version": run.get("GlueVersion") or "",
        "execution_class": run.get("ExecutionClass") or "",
        "autoscaling": _is_autoscaling(run),
        "started_on": str(run.get("StartedOn") or ""),
        "completed_on": str(run.get("CompletedOn") or ""),
    }
    if dpu_source:
        attrs["dpu_source"] = dpu_source
    # `ErrorCategory` so entra se a resposta da API trouxer o campo. Nunca e
    # inferido do texto de `ErrorMessage`, e a mensagem em si nao entra no fact:
    # ela pode carregar nome de tabela, caminho de S3 ou trecho de dado.
    if run.get("ErrorCategory"):
        attrs["error_category"] = run["ErrorCategory"]

    provenance = {"extractor": EXTRACTOR_ID, "artifact": path}
    provenance.update(dpu_provenance)

    fact = Fact(
        kind="glue.job_run",
        subject={
            "job_name": job_name,
            "job_run_id": run_id,
            "type": "job_run",
            "symbol": run_id,
        },
        measures=measures,
        attrs=attrs,
        provenance=provenance,
    )
    return fact, extras


def _load_runs(directory: Path, job_name: str) -> list[tuple[dict[str, Any], str]]:
    """Carrega os artefatos de run do diretorio, filtrados pelo job."""
    loaded: list[tuple[dict[str, Any], str]] = []
    for target in iter_source_files(directory, "*.json"):
        run = json.loads(target.read_text(encoding="utf-8"))
        if (run.get("JobName") or "") != job_name:
            continue
        loaded.append((run, str(target)))
    return loaded


def _group_key(job_name: str, run: dict[str, Any]) -> tuple[Any, ...]:
    subject = _capacity_subject(job_name, run)
    return (
        subject["glue_version"],
        subject["worker_type"],
        subject["number_of_workers"],
        subject["autoscaling"],
    )


def _dpu_source_of_group(sources: set[str]) -> str:
    """`mixed` quando o grupo agrega observado e derivado.

    Fundir os dois em silencio produziria um p95 de DPU cuja metade foi medida
    e metade calculada, sem o leitor saber qual. `mixed` e o aviso.
    """
    if len(sources) == 1:
        return next(iter(sources))
    if not sources:
        return "none"
    return "mixed"


_STATE_TO_COUNTER = {
    "SUCCEEDED": "n_succeeded",
    "FAILED": "n_failed",
    "TIMEOUT": "n_timeout",
    "STOPPED": "n_stopped",
}


def _distribution_facts(job_name: str, rows: list[dict[str, Any]], path: str) -> list[Fact]:
    """Uma distribuicao por (capacidade, estado terminal)."""
    grupos: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grupos[_group_key(job_name, row["run"]) + (row["state"],)].append(row)

    facts: list[Fact] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling, state = chave
        runtimes = sorted(
            float(m["execution_time_s"]) for m in membros if m["execution_time_s"] is not None
        )
        dpus = sorted(float(m["dpu_seconds"]) for m in membros if m["dpu_seconds"] is not None)
        starts = sorted(m["started_on"] for m in membros if m["started_on"])

        measures: dict[str, Any] = {"n": len(membros)}
        if runtimes:
            measures.update(
                {
                    "runtime_min_s": runtimes[0],
                    "runtime_p50_s": _nearest_rank(runtimes, 50),
                    "runtime_p95_s": _nearest_rank(runtimes, 95),
                    "runtime_p99_s": _nearest_rank(runtimes, 99),
                    "runtime_max_s": runtimes[-1],
                }
            )
        if dpus:
            measures.update(
                {
                    "dpu_seconds_p50": _nearest_rank(dpus, 50),
                    "dpu_seconds_p95": _nearest_rank(dpus, 95),
                }
            )

        facts.append(
            Fact(
                kind="glue.job_run.distribution",
                subject={
                    "job_name": job_name,
                    "glue_version": glue_version,
                    "worker_type": worker_type,
                    "number_of_workers": workers,
                    "autoscaling": autoscaling,
                    "state": state,
                    "type": "job_run",
                    "symbol": _capacity_symbol(
                        job_name, glue_version, worker_type, workers, autoscaling, state
                    ),
                },
                measures=measures,
                attrs={
                    "window_first": starts[0] if starts else "",
                    "window_last": starts[-1] if starts else "",
                    "dpu_source": _dpu_source_of_group(
                        {m["dpu_source"] for m in membros if m["dpu_source"]}
                    ),
                },
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        )
    return facts


def _outcome_facts(job_name: str, rows: list[dict[str, Any]], path: str) -> list[Fact]:
    """Uma contagem de desfecho por capacidade, atravessando os estados.

    Contagens, nao taxa: a divisao e juizo e pertence a fase seguinte. O fact
    carrega numerador e denominador.
    """
    grupos: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grupos[_group_key(job_name, row["run"])].append(row)

    facts: list[Fact] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave
        measures = {
            "n_total": len(membros),
            "n_succeeded": 0,
            "n_failed": 0,
            "n_timeout": 0,
            "n_stopped": 0,
        }
        for membro in membros:
            counter = _STATE_TO_COUNTER.get(membro["state"])
            if counter:
                measures[counter] += 1
        starts = sorted(m["started_on"] for m in membros if m["started_on"])

        facts.append(
            Fact(
                kind="glue.job_run.outcome",
                subject={
                    "job_name": job_name,
                    "glue_version": glue_version,
                    "worker_type": worker_type,
                    "number_of_workers": workers,
                    "autoscaling": autoscaling,
                    "type": "job_run",
                    "symbol": _capacity_symbol(
                        job_name, glue_version, worker_type, workers, autoscaling
                    ),
                },
                measures=measures,
                attrs={
                    "window_first": starts[0] if starts else "",
                    "window_last": starts[-1] if starts else "",
                },
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        )
    return facts


def _cloudwatch_artifact(job_name: str, run_id: str, cloudwatch_dir: Path | None) -> Path | None:
    if cloudwatch_dir is None:
        return None
    candidate = Path(cloudwatch_dir) / f"{job_name}_{run_id}.json"
    return candidate if candidate.is_file() else None


def _correlate(job_name: str, run_id: str, cloudwatch_dir: Path | None) -> list[Fact]:
    """Junta por `job_run_id` os facts de metrica ja coletados.

    Run sem metrica nao e erro: e lacuna com nome, razao e o comando exato que a
    resolve -- a mesma convencao que o manifesto usa para nao deixar `resume()`
    cego.
    """
    if cloudwatch_dir is None:
        return [
            _unresolved(
                job_name,
                run_id,
                "cloudwatch_not_requested",
                "Correlacao com CloudWatch nao pedida nesta analise. Para incluir, passe "
                "--cloudwatch <diretorio de artefatos cloudwatch>.",
            )
        ]

    artifact = _cloudwatch_artifact(job_name, run_id, cloudwatch_dir)
    if artifact is None:
        return [
            _unresolved(
                job_name,
                run_id,
                "cloudwatch_artifact_missing",
                "Nenhum artefato de metrica para este run no diretorio informado.",
                collect_command=(
                    f"sparkforge collect cloudwatch --repo . --job-name {job_name} "
                    f"--job-run {run_id} --start <ISO8601> --end <ISO8601> --now <ISO8601>"
                ),
            )
        ]

    return list(extract_cloudwatch_path(artifact))


def extract_glue_job_runs_path(
    directory: Path, job_name: str, cloudwatch_dir: Path | None = None
) -> list[Fact]:
    """Extrai Facts do diretorio de artefatos de run de um job.

    `cloudwatch_dir` e opcional. Ausente, os facts de distribuicao saem
    completos e a correlacao inteira vai para `unresolved` -- correlacao que
    nao aconteceu e dita, nunca omitida.
    """
    facts: list[Fact] = []
    rows: list[dict[str, Any]] = []
    runs = _load_runs(directory, job_name)

    for run, path in runs:
        fact, extras = _run_fact(job_name, run, path)
        facts.append(fact)
        facts.extend(extras)
        rows.append(
            {
                "run": run,
                "state": fact.attrs["state"],
                "started_on": fact.attrs["started_on"],
                "execution_time_s": fact.measures.get("execution_time_s"),
                "dpu_seconds": fact.measures.get("dpu_seconds"),
                "dpu_source": fact.attrs.get("dpu_source", ""),
            }
        )
        facts.extend(_correlate(job_name, run.get("Id") or "", cloudwatch_dir))

    facts.extend(_distribution_facts(job_name, rows, str(directory)))
    facts.extend(_outcome_facts(job_name, rows, str(directory)))
    facts.append(
        Fact(
            kind="glue.job_run.analyzed",
            subject={"job_name": job_name, "type": "job_run", "symbol": job_name},
            measures={
                "runs_analyzed": len(runs),
                "runs_with_metrics": sum(
                    1
                    for run, _ in runs
                    if _cloudwatch_artifact(job_name, run.get("Id") or "", cloudwatch_dir)
                ),
            },
            provenance={"extractor": EXTRACTOR_ID, "artifact": str(directory)},
        )
    )
    return sort_facts(facts)
