"""Custo em moeda por run, a partir do DPU medido e do preco publicado.

FORMA, E O PRECEDENTE QUE A JUSTIFICA. Isto e fact, e nao mecanismo, porque nao
ha limiar e nao ha juizo -- e aritmetica sobre um numero medido e uma constante
com fonte. `glue.job_run` ja carrega `dpu_seconds` derivado de um fator
documentado, com `dpu_source` nos attrs e a formula na proveniencia; custo tem
exatamente essa forma. Sendo fact, entra no motor de regras.

SOBRE `facts/pricing.py` NAO CALCULAR NADA. Aquele docstring proibe uma
combinacao especifica: preco publicado vezes o anuncio de reducao do Glue 6.0,
cujo produto seria um preco por versao que fonte nenhuma publica. Este modulo
NAO toca em `announcements`. Ele aplica o preco tal como publicado a uma
medicao, e carrega as duas ressalvas da fonte junto do numero.

AS DUAS RESSALVAS VIAJAM DENTRO DO FACT. `region` e `runtime_version` valem
`UNQUALIFIED` porque a fonte foi lida e nao qualificou nenhum dos dois eixos --
diferente de campo ausente, que diria que ninguem leu. Deixa-las no relatorio
em vez de no fact seria perde-las no primeiro salto: o fact vai para `--out`,
para a tool MCP, para o contexto de um agente.

Puro e deterministico: nunca aplica limiar, nunca atribui severidade, nunca
toca a rede.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.facts.pricing import PricingError, prices
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "run_cost@0.1.0"

EMITTED_KINDS = frozenset({"glue.run_cost", "glue.run_cost.unresolved"})

_SEGUNDOS_POR_HORA = 3600.0
_FORMULA = "dpu_hours * price_per_dpu_hour, dpu_hours = dpu_seconds / 3600"


def _run_subject(run: Fact) -> dict[str, Any]:
    return {
        "type": "job_run",
        "symbol": str(run.subject.get("job_run_id") or run.subject.get("symbol") or ""),
        "job_name": str(run.subject.get("job_name") or ""),
        "job_run_id": str(run.subject.get("job_run_id") or ""),
    }


def _unresolved(run: Fact, reason: str, detail: str, path: str) -> Fact:
    return Fact(
        kind="glue.run_cost.unresolved",
        subject=_run_subject(run),
        attrs={"reason": reason, "detail": detail},
        provenance={"extractor": EXTRACTOR_ID, "artifact": path},
    )


def _preco() -> tuple[dict[str, Any] | None, str, str]:
    """Devolve `(entrada, reason, detail)`. Entrada `None` quando nao da."""
    try:
        candidatos = prices()
    except PricingError as exc:
        return None, "price_unavailable", str(exc)
    if not candidatos:
        return None, "price_unavailable", "A tabela de preco nao tem entrada de DPU-hora."
    if len(candidatos) > 1:
        valores = ", ".join(str(c.get("value")) for c in candidatos)
        return (
            None,
            "price_ambiguous",
            f"A tabela publica mais de um preco por DPU-hora sem eixo que os separe "
            f"({valores}). Escolher um seria escolher pelo operador.",
        )
    return candidatos[0], "", ""


def extract_run_cost(facts: Sequence[Fact], path: str) -> list[Fact]:
    """Emite um `glue.run_cost` por run que tem `dpu_seconds` medido."""
    runs = [f for f in facts if f.kind == "glue.job_run"]
    if not runs:
        return []

    entrada, reason, detail = _preco()
    saida: list[Fact] = []

    for run in sorted(runs, key=lambda f: str(f.subject.get("job_run_id") or "")):
        dpu_seconds = run.measures.get("dpu_seconds")
        if dpu_seconds is None:
            saida.append(
                _unresolved(
                    run,
                    "dpu_seconds_unavailable",
                    "O run nao tem `dpu_seconds`. Sob Auto Scaling sem DPUSeconds o "
                    "coletor recusou derivar, porque `number_of_workers` e teto e nao "
                    "uso -- e sem DPU nao ha custo. Custo zero seria a mentira mais "
                    "confortavel possivel aqui.",
                    path,
                )
            )
            continue
        if entrada is None:
            saida.append(_unresolved(run, reason, detail, path))
            continue

        dpu_hours = float(dpu_seconds) / _SEGUNDOS_POR_HORA
        preco = float(entrada["value"])
        saida.append(
            Fact(
                kind="glue.run_cost",
                subject=_run_subject(run),
                measures={
                    "dpu_seconds": float(dpu_seconds),
                    "dpu_hours": dpu_hours,
                    "price_per_dpu_hour": preco,
                    "cost": dpu_hours * preco,
                },
                attrs={
                    "region": str(entrada.get("region") or ""),
                    "runtime_version": str(entrada.get("runtime_version") or ""),
                    "currency": str(entrada.get("currency") or ""),
                    "price_source": str(entrada.get("source") or ""),
                    "price_retrieved": str(entrada.get("retrieved") or ""),
                    "dpu_source": str(run.attrs.get("dpu_source") or ""),
                },
                provenance={
                    "extractor": EXTRACTOR_ID,
                    "artifact": path,
                    "formula": _FORMULA,
                },
            )
        )
    return sort_facts(saida)
