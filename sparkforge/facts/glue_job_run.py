"""Extrator do historico de runs Glue em Facts.

Le o diretorio de artefatos `glue_job_run` -- um JSON por run terminal, escrito
por `sparkforge.collect.aws.collect_glue_job_runs` -- e emite o fact por run.
Distribuicao/outcome por capacidade e correlacao com facts de CloudWatch sao
camadas futuras deste mesmo modulo, ainda nao implementadas aqui.

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
from pathlib import Path
from typing import Any

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
        subject={"job_name": job_name, "job_run_id": run_id},
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
        subject={"job_name": job_name, "job_run_id": run_id},
        measures=measures,
        attrs=attrs,
        provenance=provenance,
    )
    return fact, extras


def _load_runs(directory: Path, job_name: str) -> list[tuple[dict[str, Any], str]]:
    """Carrega os artefatos de run do diretorio, filtrados pelo job."""
    loaded: list[tuple[dict[str, Any], str]] = []
    for target in sorted(Path(directory).glob("*.json")):
        run = json.loads(target.read_text(encoding="utf-8"))
        if (run.get("JobName") or "") != job_name:
            continue
        loaded.append((run, str(target)))
    return loaded


def extract_glue_job_runs_path(directory: Path, job_name: str) -> list[Fact]:
    """Extrai Facts do diretorio de artefatos de run de um job."""
    facts: list[Fact] = []
    runs = _load_runs(directory, job_name)

    for run, path in runs:
        fact, extras = _run_fact(job_name, run, path)
        facts.append(fact)
        facts.extend(extras)

    facts.append(
        Fact(
            kind="glue.job_run.analyzed",
            subject={"job_name": job_name},
            measures={"runs_analyzed": len(runs)},
            provenance={"extractor": EXTRACTOR_ID, "artifact": str(directory)},
        )
    )
    return sort_facts(facts)
