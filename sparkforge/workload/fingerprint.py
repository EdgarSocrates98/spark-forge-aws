"""Montagem do fingerprint a partir de facts ja extraidos.

Puro sobre Facts: nao le artefato, nao toca a rede, nao mede relogio -- mesma
disciplina de `facts/benchmark.py`, que tambem opera sobre a saida de outros
verbos.

A ESCALA DE CADA EIXO DE VOLUME VEM DO HISTORICO DO PROPRIO JOB. `extreme` e o
run acima do p99 dos runs ANTERIORES daquele job, e nao um limiar universal:
nao existe fonte da AWS ou do Spark dizendo que 1 TB de varredura e muito, e
inventar o numero seria `field-heuristic` aplicada igual a um job de dez
minutos e a um de dez horas.

O historico de volume NAO vem de `glue.job_run.distribution`: aquele fact
carrega duracao e DPU, nunca bytes, porque `glue.get_job_runs` nao publica
volume lido. Ele vem da mesma medicao repetida -- um conjunto de facts por run
anterior, que `--history` entrega como um arquivo por run. Separar por arquivo
e o que identifica cada run: `execution_id` e por aplicacao, e dois event logs
diferentes colidem nele.

O custo dessa escolha e declarado, nao escondido: job sem historico coletado
nao classifica os eixos de volume. Eles saem `unknown` com o comando que
resolve, e os eixos que NAO dependem de historico -- skew e densidade de
arquivo, que ja sao razoes -- saem preenchidos assim mesmo.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sparkforge.findings.models import Fact
from sparkforge.workload.axis import Axis, unknown_axis

# O historico de volume e produzido rodando o extrator sobre os event logs
# anteriores, um arquivo por run. Nao ha comando unico que o produza de uma vez,
# e dizer o contrario mandaria o operador a um caminho que nao existe. O nome
# `collect glue-job-runs` aparece aqui so como pista de onde comeca a busca dos
# runs anteriores -- a producao do historico em si e o loop abaixo.
_PRODUZ_HISTORICO = (
    "sparkforge collect glue-job-runs --job-name <job>; depois, para cada run "
    "anterior: sparkforge analyze sql-metrics --path <event-log-do-run>.jsonl "
    "--out <dir-de-historico>/<run>.json"
)

# Menos de tres runs nao sustenta a afirmacao de um p99. Anunciar percentil
# sobre dois pontos e teatro de precisao, e o eixo prefere recusar.
_MINIMO_DE_RUNS = 3
_ANALISA_SQL = "sparkforge analyze sql-metrics --path <event-log.jsonl> --out <facts.json>"
_ANALISA_EVENT_LOG = "sparkforge analyze event-log --path <event-log.jsonl> --out <facts.json>"
_ANALISA_PLANO = "sparkforge analyze plan --path <explain.txt> --out <facts.json>"

# Razao p95/p50 de duracao de tarefa. Sao razoes, e nao volumes: comparar uma
# razao com o historico dela seria uma segunda derivada sem consumidor.
_SKEW_FAIXAS = ((10.0, "extreme"), (4.0, "high"), (2.0, "medium"))

# Arquivos por MiB lido. Densidade alta e o sintoma de small files.
_FILE_FAIXAS = ((4.0, "extreme"), (1.0, "high"), (0.25, "medium"))

# Spill (memoria + disco) sobre input, por stage. Razao interna: nao depende
# de historico.
_SPILL_FAIXAS = ((1.0, "extreme"), (0.25, "high"), (0.05, "medium"))

# Compartilhamento da fonte declarada sobre o total varrido.
_FONTE_FAIXAS = ((0.75, "extreme"), (0.4, "high"), (0.1, "medium"))

_ESTRATEGIAS_CARAS = ("CartesianProduct", "BroadcastNestedLoopJoin")


def _classe_por_faixa(valor: float, faixas: tuple[tuple[float, str], ...]) -> str:
    for limite, classe in faixas:
        if valor >= limite:
            return classe
    return "low"


def _nearest_rank(ordenados: list[float], pct: int) -> float:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n).

    Mesma formula de `event_log._nearest_rank` e dos irmaos, reescrita aqui em
    vez de importada: os modulos sao independentes por desenho, e o que
    garante que continuam iguais e teste, nao import.
    """
    n = len(ordenados)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return ordenados[rank - 1]


def _classe_por_historico(valor: float, anteriores: list[float]) -> str:
    ordenados = sorted(anteriores)
    if valor >= _nearest_rank(ordenados, 99):
        return "extreme"
    if valor >= _nearest_rank(ordenados, 95):
        return "high"
    if valor >= _nearest_rank(ordenados, 50):
        return "medium"
    return "low"


def _totais_por_run(history: Sequence[Sequence[Fact]], kind: str, measure: str) -> list[float]:
    """Um total por run anterior, somando a measure dentro de cada arquivo."""
    totais: list[float] = []
    for run in history:
        soma = sum(f.measures.get(measure, 0) for f in run if f.kind == kind)
        if soma:
            totais.append(float(soma))
    return totais


@dataclass(frozen=True)
class WorkloadFingerprint:
    job_name: str
    job_run_id: str
    axes: dict[str, Axis]
    source_count: int

    def unknown_axes(self) -> list[str]:
        """Os eixos que NAO foram respondidos, nomeados.

        Existe para que quem le o perfil saiba o que falta sem varrer campo a
        campo -- a mesma razao pela qual o manifesto lista o que nao coletou.
        """
        return sorted(nome for nome, eixo in self.axes.items() if eixo.value == "unknown")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_name": self.job_name,
            "job_run_id": self.job_run_id,
            "source_count": self.source_count,
            "axes": {nome: eixo.to_dict() for nome, eixo in self.axes.items()},
            "unknown_axes": self.unknown_axes(),
        }


def _scan_axes(
    scans: list[Fact], history: Sequence[Sequence[Fact]]
) -> dict[str, Axis]:
    eixos: dict[str, Axis] = {}

    if not scans:
        eixos["scan_intensity"] = unknown_axis("spark.sql.scan", _ANALISA_SQL)
        eixos["file_pressure"] = unknown_axis("spark.sql.scan", _ANALISA_SQL)
        return eixos

    total_bytes = sum(f.measures.get("bytes_read", 0) for f in scans)
    total_files = sum(f.measures.get("files_read", 0) for f in scans)
    evidencia = tuple(f.id for f in scans)

    anteriores = _totais_por_run(history, "spark.sql.scan", "bytes_read")
    if not anteriores:
        eixos["scan_intensity"] = unknown_axis("history_absent", _PRODUZ_HISTORICO)
    elif len(anteriores) < _MINIMO_DE_RUNS:
        eixos["scan_intensity"] = unknown_axis("history_too_short", _PRODUZ_HISTORICO)
    else:
        eixos["scan_intensity"] = Axis(
            value=_classe_por_historico(total_bytes, anteriores),
            confidence="measured",
            basis="history_percentile",
            evidence=evidencia,
        )

    # Densidade de arquivo e razao interna: responde no PRIMEIRO run, sem
    # historico nenhum.
    densidade = (total_files / (total_bytes / 1_048_576)) if total_bytes else 0.0
    eixos["file_pressure"] = Axis(
        value=_classe_por_faixa(densidade, _FILE_FAIXAS),
        confidence="measured",
        basis="files_per_mib",
        evidence=evidencia,
    )
    return eixos


def _shuffle_axis(shuffles: list[Fact], history: Sequence[Sequence[Fact]]) -> Axis:
    if not shuffles:
        return unknown_axis("spark.stage.shuffle", _ANALISA_EVENT_LOG)

    anteriores = _totais_por_run(history, "spark.stage.shuffle", "write_bytes")
    if not anteriores:
        return unknown_axis("history_absent", _PRODUZ_HISTORICO)
    if len(anteriores) < _MINIMO_DE_RUNS:
        return unknown_axis("history_too_short", _PRODUZ_HISTORICO)

    total = sum(f.measures.get("write_bytes", 0) for f in shuffles)
    return Axis(
        value=_classe_por_historico(total, anteriores),
        confidence="measured",
        basis="history_percentile",
        evidence=tuple(f.id for f in shuffles),
    )


def _skew_axis(duracoes: list[Fact]) -> Axis:
    # Razao interna ao run: nao depende de historico.
    razoes = [
        f.measures["p95_ms"] / f.measures["p50_ms"]
        for f in duracoes
        if f.measures.get("p50_ms")
    ]
    if not razoes:
        return unknown_axis("spark.stage.task_duration", _ANALISA_EVENT_LOG)
    return Axis(
        value=_classe_por_faixa(max(razoes), _SKEW_FAIXAS),
        confidence="measured",
        basis="task_p95_over_p50",
        evidence=tuple(f.id for f in duracoes),
    )


def _memory_axis(spills: list[Fact]) -> Axis:
    # Spill contra input, razao interna ao run.
    razoes = [
        (f.measures.get("memory_spill_bytes", 0) + f.measures.get("disk_spill_bytes", 0))
        / f.measures["input_bytes"]
        for f in spills
        if f.measures.get("input_bytes")
    ]
    if not razoes:
        return unknown_axis("spark.stage.spill", _ANALISA_EVENT_LOG)
    return Axis(
        value=_classe_por_faixa(max(razoes), _SPILL_FAIXAS),
        confidence="measured",
        basis="spill_over_input",
        evidence=tuple(f.id for f in spills),
    )


def _join_axis(joins: list[Fact]) -> Axis:
    # Estrutural: o `basis` diz isso -- CartesianProduct e fato do plano, nao
    # volume.
    if not joins:
        return unknown_axis("plan.join", _ANALISA_PLANO)
    caros = [f for f in joins if f.attrs.get("strategy") in _ESTRATEGIAS_CARAS]
    if caros:
        valor = "extreme"
    elif len(joins) >= 3:
        valor = "high"
    else:
        valor = "medium"
    return Axis(
        value=valor,
        confidence="measured",
        basis="plan_structure",
        evidence=tuple(f.id for f in joins),
    )


def _sla_axis(declarado: Fact | None) -> Axis:
    # Declarado: nunca promovido a `measured`.
    if declarado is None or "sla_minutes" not in declarado.measures:
        return unknown_axis(
            "workload.declared:sla_minutes", "declare o job em workload.yaml com `sla_minutes`"
        )
    valor = "critical" if declarado.measures["sla_minutes"] <= 60 else "medium"
    return Axis(
        value=valor,
        confidence="declared",
        basis="declared",
        evidence=(declarado.id,),
    )


def _primary_input_axis(declarado: Fact | None, scans: list[Fact]) -> Axis:
    fonte = declarado.attrs.get("primary_source") if declarado is not None else None
    if not fonte:
        return unknown_axis(
            "workload.declared:primary_source",
            "declare o job em workload.yaml com `primary_source`",
        )

    casados = [f for f in scans if f.subject.get("relation") == fonte]
    if not casados:
        return unknown_axis("declared_source_not_observed")

    bytes_fonte = sum(f.measures.get("bytes_read", 0) for f in casados)
    total = sum(f.measures.get("bytes_read", 0) for f in scans) or 1
    assert declarado is not None  # `fonte` so existe se `declarado` existe.
    return Axis(
        value=_classe_por_faixa(bytes_fonte / total, _FONTE_FAIXAS),
        confidence="declared",
        basis="declared_source_share",
        evidence=tuple(f.id for f in casados) + (declarado.id,),
    )


def build_fingerprint(
    facts: Sequence[Fact],
    *,
    job_name: str,
    job_run_id: str,
    history: Sequence[Sequence[Fact]] = (),
) -> WorkloadFingerprint:
    """Monta o fingerprint. Eixo sem lastro sai `unknown`, nunca um default.

    `history` e uma sequencia de conjuntos de facts, UM POR RUN ANTERIOR. A
    separacao por conjunto e o que identifica cada run.
    """
    por_kind: dict[str, list[Fact]] = {}
    for fact in facts:
        por_kind.setdefault(fact.kind, []).append(fact)

    scans = por_kind.get("spark.sql.scan") or []

    eixos: dict[str, Axis] = {}
    eixos.update(_scan_axes(scans, history))
    eixos["shuffle_intensity"] = _shuffle_axis(por_kind.get("spark.stage.shuffle") or [], history)
    eixos["skew_risk"] = _skew_axis(por_kind.get("spark.stage.task_duration") or [])
    eixos["memory_pressure"] = _memory_axis(por_kind.get("spark.stage.spill") or [])
    eixos["join_intensity"] = _join_axis(por_kind.get("plan.join") or [])

    declarados = [
        f for f in (por_kind.get("workload.declared") or []) if f.subject.get("symbol") == job_name
    ]
    declarado = declarados[0] if declarados else None
    eixos["sla_class"] = _sla_axis(declarado)
    eixos["primary_input_class"] = _primary_input_axis(declarado, scans)

    return WorkloadFingerprint(
        job_name=job_name,
        job_run_id=job_run_id,
        axes=eixos,
        source_count=len(scans),
    )
