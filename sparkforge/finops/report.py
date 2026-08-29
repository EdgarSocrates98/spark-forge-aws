"""O relatorio financeiro: custo, a troca recurso-tempo, e onde a alavanca esta.

NAO e extrator, e nada aqui vira Fact. O fact de custo e
`sparkforge/facts/run_cost.py`; este modulo COMPOE -- e composicao e leitura,
nao medicao.

A FRONTEIRA E O NUCLEO. DPU-segundos nao e invariante na troca entre mais
recurso e mais tempo: dobrar workers raramente divide o tempo por dois, e as
vezes divide por mais. Duas capacidades medidas lado a lado respondem o que
nenhum modelo responderia sem inventar um fator de eficiencia que fonte
nenhuma publica.

O QUE ESTE MODULO RECUSA:
  - Atribuir custo a causa. "Voce desperdicou X com spill" exige o custo do run
    que NAO aconteceu.
  - Interpolar entre capacidades observadas. A curva seria bonita e mentiria
    exatamente entre os pontos, que e onde alguem olharia.
  - Ordenar achado por economia estimada. Cada numero desses e um
    contrafactual disfarcado de prioridade.
  - Limiar de "caro". Fonte nenhuma diz que 2,32 USD por run e muito.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from sparkforge.capacity.plan import resolution_supports
from sparkforge.facts.run_cost import extract_run_cost
from sparkforge.findings.models import Fact

# Areas cujo achado aponta para o CODIGO ou para o layout do dado, e nao para
# a capacidade. Lista explicita, e nao prefixo generico: `SF-GLUE` e `SF-EMR`
# sao infraestrutura, e por-los aqui faria a alavanca de codigo sugerir
# consertar codigo para um problema de Terraform.
#
# A separacao existe porque trocar worker para consertar um destes e comprar
# saida de um defeito: o custo cai um pouco, o defeito fica, e a conta volta
# maior quando o volume crescer.
_AREAS_DE_CODIGO = frozenset(
    {"SF-PY", "SF-PQ", "SF-PLAN", "SF-UI", "SF-SQL", "SF-CG", "SF-GRAPH", "SF-DQ"}
)


def _area_de(rule_id: str) -> str:
    return rule_id.rsplit("-", 1)[0]


def _levers(findings: Sequence[Any]) -> dict[str, Any]:
    """Qual alavanca se aplica -- nunca QUANTO do custo e de cada lado.

    Atribuir o quanto exigiria o custo do run que nao aconteceu, e a spec
    recusa isso por escrito. O que este bloco faz e nomear a evidencia que ja
    existe, agrupada pelo eixo que faltava: o financeiro.

    A ordem e a que o `judge` devolveu. Ordenar por "economia estimada" seria
    um contrafactual disfarcado de prioridade.
    """
    de_codigo = [
        {
            "rule_id": f.rule_id,
            "title": f.title,
            "severity": f.severity,
            "subject": f.subject,
        }
        for f in findings
        if _area_de(f.rule_id) in _AREAS_DE_CODIGO
    ]
    return {
        "code": {
            "findings": de_codigo,
            "detail": (
                "Nenhum destes muda trocando worker. Um job que varre dez vezes o que "
                "precisa e caro em qualquer capacidade."
            )
            if de_codigo
            else "",
        },
        "capacity": {
            "detail": (
                "A pergunta de capacidade tem resposta com evidencia em "
                "`sparkforge capacity`, que compara as capacidades observadas contra o "
                "SLA declarado."
            )
        },
        "none_found": not de_codigo,
    }


def _nearest_rank(ordenados: list[float], pct: int) -> float:
    n = len(ordenados)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return ordenados[rank - 1]


def _capacidade(run: Fact) -> tuple[str, str, int, bool]:
    return (
        str(run.attrs.get("glue_version") or ""),
        str(run.attrs.get("worker_type") or ""),
        int(run.measures.get("number_of_workers") or 0),
        bool(run.attrs.get("autoscaling")),
    )


def _frontier(
    runs: Sequence[Fact], custo_por_run: dict[str, float]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grupos: dict[tuple[str, str, int, bool], list[Fact]] = {}
    for run in runs:
        grupos.setdefault(_capacidade(run), []).append(run)

    linhas: list[dict[str, Any]] = []
    recusas: list[dict[str, Any]] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave
        custos = sorted(
            custo_por_run[str(m.subject.get("job_run_id"))]
            for m in membros
            if str(m.subject.get("job_run_id")) in custo_por_run
        )
        if not custos:
            recusas.append(
                {
                    "reason": "cost_unobservable",
                    "capacity": f"{worker_type} x{workers}",
                    "runs": len(membros),
                    "detail": (
                        "Nenhum run desta capacidade tem custo: sem `dpu_seconds` nao ha "
                        "o que converter. Sob Auto Scaling sem DPUSeconds o coletor "
                        "recusou derivar, e a recusa se propaga ate aqui."
                    ),
                }
            )
            continue
        duracoes = sorted(
            float(m.measures["execution_time_s"])
            for m in membros
            if m.measures.get("execution_time_s") is not None
        )
        linhas.append(
            {
                "glue_version": glue_version,
                "worker_type": worker_type,
                "number_of_workers": workers,
                "autoscaling": autoscaling,
                "runs": len(membros),
                "runtime_p50_s": _nearest_rank(duracoes, 50) if duracoes else None,
                "runtime_p95_s": _nearest_rank(duracoes, 95) if duracoes else None,
                "cost_per_run_p95": _nearest_rank(custos, 95),
            }
        )

    linhas.sort(key=lambda linha: linha["cost_per_run_p95"])
    if linhas:
        barato = linhas[0]["cost_per_run_p95"]
        for linha in linhas:
            linha["cost_relative"] = (
                linha["cost_per_run_p95"] / barato if barato else None
            )
    return linhas, recusas


def _per_sla_outcome(
    runs: Sequence[Fact],
    custo_por_run: dict[str, float],
    sla_segundos: float | None,
    alvo: float | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Custo por run que ficou DENTRO do SLA.

    Curto prazo e o custo de um run; longo prazo e o custo por desfecho util.
    Uma capacidade mais barata por run que estoura o SLA com frequencia custa
    mais por resultado que serve -- e o run que estourou custou dinheiro sem
    entregar o que precisava.
    """
    if sla_segundos is None or alvo is None:
        return [], [
            {
                "reason": "sla_not_declared",
                "detail": (
                    "Sem `sla_minutes` e `reliability_target` em workload.yaml nao ha "
                    "desfecho util a contar, e custo por desfecho vira divisao por uma "
                    "definicao que ninguem deu."
                ),
            }
        ]

    grupos: dict[tuple[str, str, int, bool], list[Fact]] = {}
    for run in runs:
        grupos.setdefault(_capacidade(run), []).append(run)

    linhas: list[dict[str, Any]] = []
    recusas: list[dict[str, Any]] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave
        com_custo = [
            m for m in membros if str(m.subject.get("job_run_id")) in custo_por_run
        ]
        if not com_custo:
            continue
        n = len(com_custo)
        dentro = [
            m
            for m in com_custo
            if float(m.measures.get("execution_time_s") or 0) <= sla_segundos
        ]
        confiabilidade = len(dentro) / n
        resolucao = 1.0 / n
        if not resolution_supports(resolucao, float(alvo)):
            recusas.append(
                {
                    "reason": "resolution_too_coarse",
                    "capacity": f"{worker_type} x{workers}",
                    "runs": n,
                    "detail": (
                        f"Com {n} runs a menor diferenca observavel e {resolucao:.1%}, e o "
                        f"alvo de {float(alvo):.1%} exige distinguir {1 - float(alvo):.1%}. "
                        f"A visao de curto prazo continua valendo; a de longo nao."
                    ),
                }
            )
            continue
        # `math.fsum`, e nao `sum`: a soma ingenua de float depende da ORDEM
        # das parcelas e da VERSAO do interpretador. CPython 3.12 passou a
        # compensar a soma de float em `sum()` (Neumaier); 3.10 e 3.11 nao.
        # Medido nestes mesmos custos: a soma ingenua da 11.880000000000006 ou
        # 11.880000000000003 conforme a ordem, e `sum()` do 3.12+ da 11.88 --
        # que dividido por 6 e a diferenca entre `1.980000000000001` e
        # `1.9800000000000002`. Foi assim que um golden gravado no 3.14 passou
        # a reprovar no CI, que roda 3.10 e 3.11. `fsum` e exatamente
        # arredondada: um valor so, em qualquer ordem e em qualquer versao.
        custo_total = math.fsum(
            custo_por_run[str(m.subject.get("job_run_id"))] for m in com_custo
        )
        linhas.append(
            {
                "glue_version": glue_version,
                "worker_type": worker_type,
                "number_of_workers": workers,
                "autoscaling": autoscaling,
                "runs": n,
                "runs_within_sla": len(dentro),
                "reliability": confiabilidade,
                # O denominador e o numero de runs que SERVIRAM. O run que
                # estourou entra no numerador -- ele custou.
                "cost_per_sla_success": (
                    custo_total / len(dentro) if dentro else None
                ),
            }
        )

    linhas.sort(
        key=lambda linha: (
            linha["cost_per_sla_success"] is None,
            linha["cost_per_sla_success"] or 0.0,
        )
    )
    return linhas, recusas


def _symptoms(facts: Sequence[Fact]) -> dict[str, Any]:
    """Os sintomas medidos, AO LADO do custo -- nunca subtraidos dele."""
    saida: dict[str, Any] = {}

    duracoes = [f for f in facts if f.kind == "spark.stage.task_duration"]
    razoes = [
        f.measures["p95_ms"] / f.measures["p50_ms"]
        for f in duracoes
        if f.measures.get("p50_ms")
    ]
    if razoes:
        saida["skew_p95_over_p50"] = round(max(razoes), 2)

    spills = [f for f in facts if f.kind == "spark.stage.spill"]
    razoes_spill = [
        (f.measures.get("memory_spill_bytes", 0) + f.measures.get("disk_spill_bytes", 0))
        / f.measures["input_bytes"]
        for f in spills
        if f.measures.get("input_bytes")
    ]
    if razoes_spill:
        saida["spill_over_input"] = round(max(razoes_spill), 3)

    scans = [f for f in facts if f.kind == "spark.sql.scan"]
    if scans:
        saida["bytes_read"] = sum(f.measures.get("bytes_read", 0) for f in scans)

    util = [
        f
        for f in facts
        if f.kind == "glue.metric"
        and f.attrs.get("name") == "glue.driver.workerUtilization"
    ]
    if util:
        saida["worker_utilization_p50"] = min(f.measures["p50"] for f in util)

    return saida


def build_finops_report(
    facts: Sequence[Fact],
    *,
    job_name: str,
    findings: Sequence[Any] = (),
) -> dict[str, Any]:
    """Compoe o relatorio financeiro a partir de facts ja extraidos."""
    runs = [
        f
        for f in facts
        if f.kind == "glue.job_run" and f.subject.get("job_name") == job_name
    ]
    custos = extract_run_cost(runs, "<facts>")
    custo_por_run = {
        str(c.subject.get("job_run_id")): float(c.measures["cost"])
        for c in custos
        if c.kind == "glue.run_cost"
    }

    frontier, recusas = _frontier(runs, custo_por_run)

    declarados = [
        f
        for f in facts
        if f.kind == "workload.declared" and f.subject.get("symbol") == job_name
    ]
    declarado = declarados[0] if declarados else None
    sla_segundos = (
        float(declarado.measures["sla_minutes"]) * 60.0
        if declarado and "sla_minutes" in declarado.measures
        else None
    )
    alvo = declarado.measures.get("reliability_target") if declarado else None

    por_desfecho, recusas_sla = _per_sla_outcome(
        runs, custo_por_run, sla_segundos, alvo
    )

    return {
        "job_name": job_name,
        "currency": next(
            (c.attrs["currency"] for c in custos if c.kind == "glue.run_cost"), ""
        ),
        "region": next(
            (c.attrs["region"] for c in custos if c.kind == "glue.run_cost"), ""
        ),
        "runtime_version": next(
            (c.attrs["runtime_version"] for c in custos if c.kind == "glue.run_cost"),
            "",
        ),
        "frontier": frontier,
        "per_sla_outcome": por_desfecho,
        "symptoms": _symptoms(facts),
        "levers": _levers(findings),
        "refused": recusas + recusas_sla,
    }
