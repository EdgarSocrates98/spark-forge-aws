"""Escolha de capacidade sob restricao de SLA.

MINIMIZE dpu_seconds  sujeito a  P(runtime <= SLA) >= reliability_target.

Entre as capacidades que cumprem o SLA, escolhe a mais BARATA -- nao a mais
rapida. Uma capacidade que corre em 3 minutos quando o SLA e 15 nao esta
ganhando nada; esta gastando.

TRES RECUSAS SUSTENTAM TUDO O QUE ESTE MODULO AFIRMA:

  1. So capacidade OBSERVADA entra. Extrapolar para uma nunca rodada exigiria
     uma lei de escala que fonte nenhuma publica, e o numero inventado
     escolheria quanto alguem gasta.
  2. So run COMPARAVEL conta. O historico mistura dias grandes e pequenos, e
     uma capacidade pode ter cumprido o SLA porque a maioria dos runs foi de
     dia pequeno.
  3. A RESOLUCAO e declarada. Com n runs a estimativa nao distingue nada mais
     fino que 1/n; alvo mais fino que isso e recusa, nao aprovacao.

NAO e um extrator, e nada aqui vira Fact: escolher capacidade e juizo, e fact
nao julga. Mesmo molde do `WorkloadFingerprint`.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sparkforge.findings.models import Fact

# `worker change` e REVIEW na secao 34 do documento de origem, que diz para
# nunca aplicar REVIEW automaticamente em producao. Nao ha caminho neste
# modulo que aplique coisa alguma.
_SAFETY = "REVIEW"

_TOLERANCIA_PADRAO = 0.25
_ALVO_PADRAO = 0.95


def _nearest_rank(ordenados: list[float], pct: int) -> float:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n)."""
    n = len(ordenados)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return ordenados[rank - 1]


@dataclass(frozen=True)
class Candidate:
    glue_version: str
    worker_type: str
    number_of_workers: int
    autoscaling: bool
    runs_total: int
    runs_comparable: int
    runs_within_sla: int
    reliability: float
    resolution: float
    dpu_seconds_p95: float
    meets_sla: bool
    safety: str = _SAFETY

    def to_dict(self) -> dict[str, Any]:
        return {
            "glue_version": self.glue_version,
            "worker_type": self.worker_type,
            "number_of_workers": self.number_of_workers,
            "autoscaling": self.autoscaling,
            "runs_total": self.runs_total,
            "runs_comparable": self.runs_comparable,
            "runs_within_sla": self.runs_within_sla,
            "reliability": self.reliability,
            "resolution": self.resolution,
            "dpu_seconds_p95": self.dpu_seconds_p95,
            "meets_sla": self.meets_sla,
            "safety": self.safety,
        }


@dataclass(frozen=True)
class CapacityPlan:
    job_name: str
    job_run_id: str
    sla_minutes: float | None
    reliability_target: float | None
    volume_tolerance: float | None
    current_volume_bytes: int | None
    candidates: list[Candidate] = field(default_factory=list)
    chosen: Candidate | None = None
    refused: list[dict[str, Any]] = field(default_factory=list)
    discarded_runs: dict[str, int] = field(default_factory=dict)
    only_one_capacity_observed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_name": self.job_name,
            "job_run_id": self.job_run_id,
            "sla_minutes": self.sla_minutes,
            "reliability_target": self.reliability_target,
            "volume_tolerance": self.volume_tolerance,
            "current_volume_bytes": self.current_volume_bytes,
            "candidates": [c.to_dict() for c in self.candidates],
            "chosen": self.chosen.to_dict() if self.chosen else None,
            "refused": self.refused,
            "discarded_runs": self.discarded_runs,
            "only_one_capacity_observed": self.only_one_capacity_observed,
        }


def _volume_de(facts: Sequence[Fact]) -> int | None:
    """Bytes varridos, somando os scans. `None` quando nenhum scan os publicou."""
    total = 0
    visto = False
    for fact in facts:
        if fact.kind != "spark.sql.scan":
            continue
        bytes_read = fact.measures.get("bytes_read")
        if bytes_read is None:
            continue
        visto = True
        total += int(bytes_read)
    return total if visto else None


def _capacidade_de(run: Fact) -> tuple[str, str, int, bool]:
    return (
        str(run.attrs.get("glue_version") or ""),
        str(run.attrs.get("worker_type") or ""),
        int(run.measures.get("number_of_workers") or 0),
        bool(run.attrs.get("autoscaling")),
    )


def build_capacity_plan(
    facts: Sequence[Fact],
    *,
    job_name: str,
    job_run_id: str,
    history: Sequence[Sequence[Fact]] = (),
) -> CapacityPlan:
    """Monta o plano. `history` e uma sequencia de conjuntos, UM POR RUN anterior."""
    declarados = [
        f
        for f in facts
        if f.kind == "workload.declared" and f.subject.get("symbol") == job_name
    ]
    declarado = declarados[0] if declarados else None

    sla_minutes = declarado.measures.get("sla_minutes") if declarado else None
    alvo = declarado.measures.get("reliability_target") if declarado else None
    tolerancia = declarado.measures.get("volume_tolerance") if declarado else None
    if alvo is None:
        alvo = _ALVO_PADRAO if declarado else None
    if tolerancia is None:
        tolerancia = _TOLERANCIA_PADRAO if declarado else None

    volume_atual = _volume_de(facts)
    descartados: dict[str, int] = {}
    recusas: list[dict[str, Any]] = []

    if sla_minutes is None:
        recusas.append(
            {
                "reason": "sla_not_declared",
                "detail": (
                    "Sem `sla_minutes` em workload.yaml para este job nao ha restricao a "
                    "satisfazer, e sem restricao a escolha e apenas a mais barata -- que "
                    "seria a recomendacao errada."
                ),
            }
        )
        return CapacityPlan(
            job_name=job_name,
            job_run_id=job_run_id,
            sla_minutes=None,
            reliability_target=alvo,
            volume_tolerance=tolerancia,
            current_volume_bytes=volume_atual,
            refused=recusas,
        )

    sla_segundos = float(sla_minutes) * 60.0

    # Agrupa os runs por capacidade, guardando duracao, dpu e volume de cada um.
    grupos: dict[tuple[str, str, int, bool], list[dict[str, Any]]] = {}
    for conjunto in history:
        runs = [f for f in conjunto if f.kind == "glue.job_run"]
        if len(runs) != 1:
            descartados["history_file_not_one_run"] = (
                descartados.get("history_file_not_one_run", 0) + 1
            )
            continue
        run = runs[0]
        duracao = run.measures.get("execution_time_s")
        if duracao is None:
            descartados["runtime_unknown"] = descartados.get("runtime_unknown", 0) + 1
            continue
        volume = _volume_de(conjunto)
        grupos.setdefault(_capacidade_de(run), []).append(
            {
                "duracao": float(duracao),
                "dpu": run.measures.get("dpu_seconds"),
                "volume": volume,
            }
        )

    candidatos: list[Candidate] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave

        comparaveis = []
        for membro in membros:
            if membro["volume"] is None:
                descartados["volume_unknown"] = descartados.get("volume_unknown", 0) + 1
                continue
            if volume_atual is None:
                comparaveis.append(membro)
                continue
            limite = volume_atual * float(tolerancia)
            if abs(membro["volume"] - volume_atual) <= limite:
                comparaveis.append(membro)

        if not comparaveis:
            recusas.append(
                {
                    "reason": "no_comparable_runs",
                    "capacity": f"{worker_type} x{workers}",
                    "runs_total": len(membros),
                    "detail": (
                        "Nenhum run desta capacidade tem volume dentro da tolerancia do run "
                        "corrente. A evidencia existe, mas nao se aplica a hoje."
                    ),
                }
            )
            continue

        custos = sorted(m["dpu"] for m in comparaveis if m["dpu"] is not None)
        if not custos:
            recusas.append(
                {
                    "reason": "cost_unobservable",
                    "capacity": f"{worker_type} x{workers}",
                    "runs_comparable": len(comparaveis),
                    "detail": (
                        "Nenhum run comparavel tem `dpu_seconds` medido. Sob Auto Scaling "
                        "sem DPUSeconds, `number_of_workers` e teto e nao uso, e o coletor "
                        "recusou derivar -- sem custo nao ha o que minimizar."
                    ),
                }
            )
            continue

        n = len(comparaveis)
        dentro = sum(1 for m in comparaveis if m["duracao"] <= sla_segundos)
        confiabilidade = dentro / n
        resolucao = 1.0 / n

        cabe = confiabilidade >= float(alvo)
        # Epsilon absorve o erro de ponto flutuante de `1.0 - alvo` (ex.:
        # 1.0 - 0.9 == 0.09999999999999998): sem ele, um `n` exatamente no
        # limite da resolucao seria recusado por artefato de representacao,
        # nao pela regra.
        if cabe and resolucao > (1.0 - float(alvo)) + 1e-9:
            # A contagem diz que cabe, e a contagem nao tem resolucao para
            # sustentar a afirmacao. Recusa, nao aprovacao.
            cabe = False
            necessarios = math.ceil(1.0 / (1.0 - float(alvo))) if alvo < 1 else 0
            recusas.append(
                {
                    "reason": "resolution_too_coarse",
                    "capacity": f"{worker_type} x{workers}",
                    "runs_comparable": n,
                    "runs_needed": necessarios,
                    "detail": (
                        f"Com {n} runs comparaveis a menor diferenca observavel e "
                        f"{resolucao:.1%}, e o alvo de {float(alvo):.1%} exige distinguir "
                        f"{1 - float(alvo):.1%}. Sao precisos ao menos {necessarios} runs."
                    ),
                }
            )

        candidatos.append(
            Candidate(
                glue_version=glue_version,
                worker_type=worker_type,
                number_of_workers=workers,
                autoscaling=autoscaling,
                runs_total=len(membros),
                runs_comparable=n,
                runs_within_sla=dentro,
                reliability=confiabilidade,
                resolution=resolucao,
                dpu_seconds_p95=_nearest_rank(custos, 95),
                meets_sla=cabe,
            )
        )

    candidatos.sort(key=lambda c: (c.dpu_seconds_p95, c.worker_type, c.number_of_workers))
    escolhido = next((c for c in candidatos if c.meets_sla), None)

    return CapacityPlan(
        job_name=job_name,
        job_run_id=job_run_id,
        sla_minutes=float(sla_minutes),
        reliability_target=float(alvo),
        volume_tolerance=float(tolerancia),
        current_volume_bytes=volume_atual,
        candidates=candidatos,
        chosen=escolhido,
        refused=recusas,
        discarded_runs=descartados,
        only_one_capacity_observed=len(grupos) == 1,
    )
