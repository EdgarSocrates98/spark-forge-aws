"""Realized Gain Ledger (§21): o ganho OBSERVADO entre runs medidos.

O SparkForge recusa estimar ganho (regra 13: exige o custo do run que nao
aconteceu). Este modulo publica o outro lado: com runs que JA aconteceram antes e
depois de uma mudanca, quanto o tempo, os DPU-segundos e o custo mudaram -- por
lado, N, mediana, minimo e maximo, e o delta das medianas.

O delta sai sempre, e as marcas dizem quando ele NAO e ganho:
- `amostra_insuficiente`: menos de 3 runs num lado;
- `volume_diverge` / `volume_desconhecido`: o mesmo criterio de volume do
  capacity (`_volume_de`, tolerancia de `workload.declared`, padrao 0,25);
- `custo_indisponivel`: run sem `glue.run_cost` ou moedas diferentes (regra 14).

E tres coisas sao recusadas sempre: economia mensal (projecao sobre runs que nao
aconteceram, regras 12 e 13), atribuicao causal (sem run de controle, o delta
mistura a mudanca com tudo que mudou junto) e intervalo de confianca (amostra
pequena: mediana e faixa no lugar).
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from statistics import median
from typing import Any

from sparkforge.capacity.plan import _TOLERANCIA_PADRAO, _volume_de
from sparkforge.findings.models import Fact

METRICAS = ("execution_time_s", "dpu_seconds", "cost")
MINIMO_DE_RUNS = 3
REFUSED: tuple[dict[str, str], ...] = (
    {"field": "economia_mensal", "reason": "projecao_sobre_runs_que_nao_aconteceram"},
    {"field": "atribuicao_causal", "reason": "sem_run_de_controle"},
    {"field": "intervalo_de_confianca", "reason": "amostra_pequena_use_mediana_e_faixa"},
)


class GainError(ValueError):
    """Entrada que nao pode ser comparada (jobs diferentes, lado sem run valido)."""


def _runs(conjuntos: Sequence[Sequence[Fact]]) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Os runs `SUCCEEDED` de um lado, com custo pelo `job_run_id` e volume so
    quando o conjunto (um arquivo) tem um run -- senao o scan nao e ligavel."""
    runs: list[dict[str, Any]] = []
    descartados: Counter[str] = Counter()
    for conjunto in conjuntos:
        execucoes = [f for f in conjunto if f.kind == "glue.job_run"]
        custos = {
            str(f.subject.get("job_run_id")): f for f in conjunto if f.kind == "glue.run_cost"
        }
        volume = _volume_de(conjunto) if len(execucoes) == 1 else None
        for run in execucoes:
            if str(run.attrs.get("state") or "").upper() != "SUCCEEDED":
                descartados["run_nao_sucedido"] += 1
                continue
            custo = custos.get(str(run.subject.get("job_run_id")))
            runs.append(
                {
                    "job_name": str(run.subject.get("job_name") or run.subject.get("symbol") or ""),
                    "execution_time_s": run.measures.get("execution_time_s"),
                    "dpu_seconds": run.measures.get("dpu_seconds"),
                    "cost": custo.measures.get("cost") if custo else None,
                    "currency": custo.attrs.get("currency") if custo else None,
                    "volume": volume,
                    "capacity": (
                        str(run.attrs.get("glue_version") or ""),
                        str(run.attrs.get("worker_type") or ""),
                        run.measures.get("number_of_workers"),
                        bool(run.attrs.get("autoscaling")),
                    ),
                }
            )
    return runs, descartados


def _resumo(valores: list[float]) -> dict[str, Any]:
    if not valores:
        return {"n": 0, "median": None, "min": None, "max": None}
    return {"n": len(valores), "median": median(valores), "min": min(valores), "max": max(valores)}


def _tolerancia(conjuntos: Sequence[Sequence[Fact]], job_name: str) -> float:
    for conjunto in conjuntos:
        for fact in conjunto:
            if fact.kind == "workload.declared" and fact.subject.get("symbol") == job_name:
                valor = fact.measures.get("volume_tolerance")
                if valor is not None:
                    return float(valor)
    return float(_TOLERANCIA_PADRAO)


def _lado(runs: list[dict[str, Any]], volumes: list[float]) -> dict[str, Any]:
    contagem = Counter(r["capacity"] for r in runs)
    return {
        "runs": len(runs),
        "capacities": [
            {"glue_version": gv, "worker_type": wt, "number_of_workers": n,
             "autoscaling": auto, "runs": quantos}
            for (gv, wt, n, auto), quantos in sorted(contagem.items(), key=lambda i: str(i[0]))
        ],
        "volume_median_bytes": median(volumes) if volumes else None,
    }


def realized_gain(
    baseline: Sequence[Sequence[Fact]], candidate: Sequence[Sequence[Fact]]
) -> dict[str, Any]:
    """O ganho observado entre os runs de `baseline` e os de `candidate`.

    Cada lado e uma lista de conjuntos de facts, um por arquivo. Levanta
    `GainError` quando os lados sao de jobs diferentes ou um lado nao tem run
    `SUCCEEDED`.
    """
    base, descartados = _runs(baseline)
    cand, descartados_cand = _runs(candidate)
    descartados.update(descartados_cand)
    vazios = [nome for nome, runs in (("baseline", base), ("candidate", cand)) if not runs]
    if vazios:
        raise GainError(f"sem run SUCCEEDED em: {', '.join(vazios)}")
    jobs = sorted({r["job_name"] for r in base + cand})
    if len(jobs) != 1:
        raise GainError(f"jobs diferentes entre os lados: {', '.join(jobs)}")
    job_name = jobs[0]
    tolerancia = _tolerancia([*baseline, *candidate], job_name)

    volumes_base = [float(r["volume"]) for r in base if r["volume"] is not None]
    volumes_cand = [float(r["volume"]) for r in cand if r["volume"] is not None]
    comuns: list[str] = []
    if len(base) < MINIMO_DE_RUNS or len(cand) < MINIMO_DE_RUNS:
        comuns.append("amostra_insuficiente")
    if not volumes_base or not volumes_cand:
        comuns.append("volume_desconhecido")
    elif abs(median(volumes_cand) - median(volumes_base)) > tolerancia * median(volumes_base):
        comuns.append("volume_diverge")

    moedas = sorted({str(r["currency"]) for r in base + cand if r["cost"] is not None})
    metricas: dict[str, Any] = {}
    for nome in METRICAS:
        valores_base = [float(r[nome]) for r in base if r[nome] is not None]
        valores_cand = [float(r[nome]) for r in cand if r[nome] is not None]
        resumo_base, resumo_cand = _resumo(valores_base), _resumo(valores_cand)
        marcas = list(comuns)
        if nome == "cost" and (
            len(valores_base) < len(base) or len(valores_cand) < len(cand) or len(moedas) > 1
        ):
            marcas.append("custo_indisponivel")
        delta = None
        if resumo_base["median"] is not None and resumo_cand["median"] is not None:
            delta = resumo_cand["median"] - resumo_base["median"]
        percentual = None
        if delta is not None and resumo_base["median"]:
            percentual = round(delta / resumo_base["median"] * 100, 1)
        metricas[nome] = {
            "baseline": resumo_base,
            "candidate": resumo_cand,
            "delta": delta,
            "delta_pct": percentual,
            "marks": marcas,
        }

    return {
        "job_name": job_name,
        "baseline": _lado(base, volumes_base),
        "candidate": _lado(cand, volumes_cand),
        "metrics": metricas,
        "currency": moedas[0] if len(moedas) == 1 else None,
        "discarded": {"run_nao_sucedido": descartados["run_nao_sucedido"]},
        "volume_tolerance": tolerancia,
        "refused": [dict(item) for item in REFUSED],
    }
