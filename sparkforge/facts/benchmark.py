"""Comparador de duas execucoes, derivado de Facts de event log.

Funcao PURA sobre `Fact`: nunca le artefato bruto, nunca executa Spark, nunca
chama AWS. A entrada e o que `analyze event-log` ja produz para cada uma das
duas execucoes -- e o motor de regras nao consegue compara-las, porque
`engine._condition_candidates` avalia UM fact por vez. Mesmo padrao de
`call_graph.py` e de `SF-EMR-008`: quem enxerga os dois lados decide e emite; o
catalogo le atributo de um fact so.

O QUE ESTE MODULO NAO PODE AFIRMAR, e por que o nome diz isso:

`total_task_ms` e a soma de `mean_ms * task_count` sobre os stages -- TEMPO DE
TASK, que e trabalho, e nao tempo de relogio. Nao existe fact de duracao de
relogio no event log lido: `event_log.py` emite duracao por stage
(`spark.stage.task_duration`) e nada de wall-clock. Um job pode terminar antes
no relogio e somar MAIS tempo de task, se passou a paralelizar melhor -- e o
inverso tambem acontece, com menos paralelismo e o mesmo trabalho. Chamar isso
de `duration_ms` seria o defeito que a Fase 5b corrigiu em
`unreachable_function_count` -- nome que promete mais do que entrega -- e aqui o
preco seria maior, porque a regra que le a medida acusa regressao.

Tres formas de dizer "nao sei", nenhuma delas zero:

  * `_delta_pct` e OMITIDO quando o lado antes e zero. Dividir por zero nao
    produz "infinito por cento", produz afirmacao sem sentido; chave ausente e
    como este motor diz "nao sei", e `engine._where_matches` reprova caminho
    ausente, entao a regra simplesmente nao avalia.
  * medida ausente dos DOIS lados nao entra em `bench.run_delta`: vira
    `bench.unresolved` nomeando a medida.
  * medida presente num lado so entra com o valor do lado que a tem, sem
    `_delta_pct`, mais um `bench.unresolved` dizendo qual lado faltou. Preencher
    o lado ausente com zero afirmaria uma queda (ou uma subida) que ninguem
    observou.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "benchmark@0.1.0"

# Os cinco kinds do namespace. `bench.stage_delta` e `bench.unmatched` so passam
# a ser EMITIDOS na Task 2 (casamento de stage por `symbol`); estao declarados
# desde ja porque a assercao final deste modulo compara o emitido contra esta
# lista, e porque o namespace e contrato do modulo, nao diario de implementacao.
EMITTED_KINDS = frozenset(
    {
        "bench.run_delta",
        "bench.stage_delta",
        "bench.unmatched",
        "bench.analyzed",
        "bench.unresolved",
    }
)


def _num(value: Any) -> float:
    """Numero, ou zero para o que nao for numero. `bool` fica de fora de
    proposito: `True` somaria 1 a um total de bytes."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int | float):
        return value
    return 0


def _task_ms(measures: dict[str, Any]) -> float:
    return _num(measures.get("mean_ms")) * _num(measures.get("task_count"))


def _input_bytes(measures: dict[str, Any]) -> float:
    return _num(measures.get("total_bytes"))


def _spill_bytes(measures: dict[str, Any]) -> float:
    return _num(measures.get("total_memory_spill_bytes")) + _num(
        measures.get("total_disk_spill_bytes")
    )


def _gc_ms(measures: dict[str, Any]) -> float:
    return _num(measures.get("gc_ms"))


def _task_count(measures: dict[str, Any]) -> float:
    return _num(measures.get("task_count"))


# (nome da medida, kind que a sustenta, como extrair a parcela de um fact).
#
# O kind e o criterio de PRESENCA: sem nenhum fact daquele kind num lado, a
# medida esta ausente ali -- e ausente nao e zero. `total_task_count` vem de
# `spark.stage.task_count` e nao do `task_count` de `spark.stage.task_duration`:
# o primeiro conta as tasks declaradas pelo stage (inclusive as que falharam),
# o segundo conta as amostras de duracao que o log trouxe.
_RUN_MEASURES: tuple[tuple[str, str, Callable[[dict[str, Any]], float]], ...] = (
    ("total_task_ms", "spark.stage.task_duration", _task_ms),
    ("total_input_bytes", "spark.stage.task_input", _input_bytes),
    ("total_spill_bytes", "spark.job.spill_summary", _spill_bytes),
    ("total_gc_ms", "spark.stage.gc", _gc_ms),
    ("total_task_count", "spark.stage.task_count", _task_count),
)


def _run_subject(path_hint: str) -> dict[str, Any]:
    return {"type": "job_run", "symbol": path_hint or "benchmark"}


def _unresolved_subject(path_hint: str, detail: str) -> dict[str, Any]:
    """Subject proprio por motivo. `Fact.id` e sha1 de (kind, subject,
    measures) -- `attrs` fica FORA --, entao dois `bench.unresolved` com o mesmo
    subject e sem measures teriam o mesmo id e seriam indistinguiveis na
    saida."""
    return {"type": "job_run", "symbol": f"{path_hint or 'benchmark'}#{detail}"}


def _round(value: float) -> float:
    """Corta o ruido de ponto flutuante que vem de `mean_ms` (uma media) sem
    tocar nas medidas inteiras -- byte e contagem de task continuam inteiros."""
    if isinstance(value, float):
        return round(value, 3)
    return value


def _delta_pct(before: float, after: float) -> float | None:
    """Variacao relativa. `None` quando o lado ANTES e zero -- dividir por zero
    ali nao produz "infinito por cento", produz uma afirmacao sem sentido."""
    if before == 0:
        return None
    return round((after - before) / before * 100, 1)


def _side_totals(facts: Sequence[Fact]) -> dict[str, tuple[bool, float]]:
    """Por medida: (o kind que a sustenta apareceu neste lado, total somado)."""
    totals: dict[str, tuple[bool, float]] = {}
    for name, kind, project in _RUN_MEASURES:
        present = False
        total: float = 0
        for fact in facts:
            if fact.kind != kind:
                continue
            present = True
            measures = fact.measures if isinstance(fact.measures, dict) else {}
            total += project(measures)
        totals[name] = (present, _round(total))
    return totals


def _artifacts_of(facts: Sequence[Fact]) -> list[str]:
    """Os artefatos que originaram este lado, sem presumir que ha exatamente um:
    event log rolante e extracao de varios arquivos produzem mais de um
    `spark.log_analyzed` para a mesma execucao."""
    artifacts: set[str] = set()
    for fact in facts:
        if fact.kind != "spark.log_analyzed":
            continue
        subject = fact.subject if isinstance(fact.subject, dict) else {}
        artifact = fact.provenance.get("artifact") or subject.get("file") or ""
        if artifact:
            artifacts.add(str(artifact))
    return sorted(artifacts)


def _stage_keys(facts: Sequence[Fact]) -> set[tuple[str, str]]:
    """Identidade de stage DENTRO de um run: (stage_id, symbol). Varios kinds
    (`duration`, `input`, `spill`, `gc`, `task_count`) descrevem o mesmo stage,
    entao a contagem e de subjects distintos, nao de facts."""
    keys: set[tuple[str, str]] = set()
    for fact in facts:
        subject = fact.subject if isinstance(fact.subject, dict) else {}
        if subject.get("type") != "stage":
            continue
        keys.add((str(subject.get("stage_id", "")), str(subject.get("symbol", ""))))
    return keys


def build_benchmark(
    before: Sequence[Fact], after: Sequence[Fact], path_hint: str = ""
) -> list[Fact]:
    """Compara os Facts de duas execucoes e emite os fatos `bench.*`.

    `before` e `after` sao o que `analyze event-log` produziu para cada
    execucao. `path_hint` ancora o subject dos fatos derivados -- normalmente
    `"<antes>..<depois>"`, porque o fato afirma sobre o PAR, e nao sobre um dos
    dois logs.

    Sem `spark.log_analyzed` num dos lados nao ha comparacao: o extrator ou nao
    rodou ali, ou rodou sobre coisa que nao e event log. A saida nesse caso e um
    unico `bench.unresolved` -- e nao um delta com um lado zerado, que afirmaria
    que a execucao daquele lado nao fez trabalho nenhum.
    """
    provenance = {
        "artifact": path_hint,
        "artifact_sha256": "",
        "extractor": EXTRACTOR_ID,
    }
    out: list[Fact] = []

    missing = [
        side
        for side, source in (("before", before), ("after", after))
        if not any(f.kind == "spark.log_analyzed" for f in source)
    ]
    if missing:
        out.append(
            Fact(
                kind="bench.unresolved",
                subject=_unresolved_subject(path_hint, "missing_log_analyzed"),
                attrs={
                    "reason": "missing_log_analyzed",
                    "sides": missing,
                    "measure": "",
                },
                provenance=provenance,
            )
        )
        return sort_facts(out)

    before_totals = _side_totals(before)
    after_totals = _side_totals(after)

    measures: dict[str, Any] = {}
    unresolved: list[tuple[str, str, list[str]]] = []
    for name, _kind, _project in _RUN_MEASURES:
        before_present, before_value = before_totals[name]
        after_present, after_value = after_totals[name]

        absent_sides = [
            side
            for side, present in (("before", before_present), ("after", after_present))
            if not present
        ]
        if len(absent_sides) == 2:
            unresolved.append((name, "measure_absent_both_sides", absent_sides))
            continue

        if before_present:
            measures[f"{name}_before"] = before_value
        if after_present:
            measures[f"{name}_after"] = after_value
        if absent_sides:
            unresolved.append((name, "measure_absent_one_side", absent_sides))
            continue

        pct = _delta_pct(before_value, after_value)
        if pct is not None:
            measures[f"{name}_delta_pct"] = pct

    before_artifacts = _artifacts_of(before)
    after_artifacts = _artifacts_of(after)

    out.append(
        Fact(
            kind="bench.run_delta",
            subject=_run_subject(path_hint),
            measures=measures,
            attrs={
                "before_artifacts": before_artifacts,
                "after_artifacts": after_artifacts,
            },
            provenance=provenance,
        )
    )

    # bench.analyzed -- a sentinela.
    #
    # Ela prova que a comparacao rodou: sem ela, "nenhum achado" e "nunca
    # comparei" ficam indistinguiveis, exatamente como em
    # `spark.log_analyzed`/`pyspark.module_analyzed`. Ela tambem NOMEIA os dois
    # lados, que e a defesa contra antes e depois trocados -- inversao aparece
    # como regressao implausivel ao lado dos artefatos, nao como silencio.
    #
    # `matched_stage_count` e `unmatched_stage_count` sao zero ate a Task 2, que
    # implementa o casamento por `symbol`.
    out.append(
        Fact(
            kind="bench.analyzed",
            subject=_run_subject(path_hint),
            measures={
                "matched_stage_count": 0,
                "unmatched_stage_count": 0,
                "before_stage_count": len(_stage_keys(before)),
                "after_stage_count": len(_stage_keys(after)),
            },
            attrs={
                "before_artifacts": before_artifacts,
                "after_artifacts": after_artifacts,
            },
            provenance=provenance,
        )
    )

    for name, reason, sides in unresolved:
        out.append(
            Fact(
                kind="bench.unresolved",
                subject=_unresolved_subject(path_hint, name),
                attrs={"reason": reason, "sides": sides, "measure": name},
                provenance=provenance,
            )
        )

    unknown = {f.kind for f in out} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(out)
