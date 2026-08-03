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

Quatro formas de dizer "nao sei", nenhuma delas zero:

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
  * presenca e por CHAVE, nao por kind (ver `_RUN_MEASURES`), e lado PARCIAL --
    parte dos facts do kind com a chave, parte sem -- tambem e ausencia. Somar
    so os facts completos produz um PISO, e piso de um lado contra total do
    outro fabrica melhora: `SF-BENCH-002` acusaria regressao inexistente, ou
    calaria uma real. Errar para o silencio e o lado certo aqui.

CASAMENTO DE STAGE, ESTRITO POR `symbol` IDENTICO:

`stage_id` nao e estavel entre execucoes, e o `symbol` -- derivado do codigo --
muda exatamente quando a mudanca foi significativa. Um benchmark existe porque o
codigo mudou. Entao nao ha casamento por posicao, por `stage_id`, por prefixo
nem por similaridade de nome: `symbol` identico ou nada. O que nao casa vira
`bench.unmatched` e e CONTADO em `bench.analyzed` -- casados mais nao casados
fecham a conta dos dois lados --, nunca omitido. Simbolo vazio ou ausente nao
casa com nada: casar dois vazios juntaria stages que so tem em comum o fato de
nao terem nome.

O recorte de stage e o SIMBOLO, nao o stage: o mesmo `symbol` pode nascer varias
vezes num run (linha dentro de laco, funcao chamada duas vezes), e as medidas
somam os stages dele. `before_stage_count`/`after_stage_count` no proprio delta
dizem quantos entraram de cada lado -- sem eles, um stage que sumiu seria lido
como stage que acelerou.
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


def _read(measures: dict[str, Any], key: str) -> float | None:
    """O valor numerico da chave, ou `None` quando ela nao da para somar.

    `None` -- e nao zero -- para chave ausente, para texto e para `bool`:
    `True` somaria 1 a um total de bytes, e `"400"` nao e uma medida, e um
    campo que alguem preencheu errado. Zero aqui seria observacao inventada.
    """
    if key not in measures:
        return None
    value = measures[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return value


def _product(values: dict[str, float]) -> float:
    total = 1.0
    for value in values.values():
        total *= value
    return total


def _total(values: dict[str, float]) -> float:
    return sum(values.values())


# (nome da medida, kind que a sustenta, chaves EXIGIDAS, como combinar).
#
# A presenca e por CHAVE, nao por kind: um fact do kind certo sem a chave certa
# nao sustenta a medida, e um lado onde nenhum fact contribuinte carrega a chave
# esta ausente ali. Hoje `event_log.py` co-emite as chaves de cada kind
# (`mean_ms` sai junto com `task_count`, memoria junto com disco), entao a
# distincao e inalcancavel por ele -- mas a partir do verbo `benchmark` a
# entrada e um ARQUIVO de facts, que alguem edita, que outra ferramenta gera e
# que uma versao futura do extrator preenche diferente. Aferir por kind
# transformaria isso em zero silencioso.
#
# `total_task_count` vem de `spark.stage.task_count` e nao do `task_count` de
# `spark.stage.task_duration`: o primeiro conta as tasks declaradas pelo stage
# (inclusive as que falharam), o segundo conta as amostras de duracao que o log
# trouxe.
_MeasureSpec = tuple[tuple[str, str, tuple[str, ...], Callable[[dict[str, float]], float]], ...]

_RUN_MEASURES: _MeasureSpec = (
    ("total_task_ms", "spark.stage.task_duration", ("mean_ms", "task_count"), _product),
    ("total_input_bytes", "spark.stage.task_input", ("total_bytes",), _total),
    (
        "total_spill_bytes",
        "spark.job.spill_summary",
        ("total_memory_spill_bytes", "total_disk_spill_bytes"),
        _total,
    ),
    ("total_gc_ms", "spark.stage.gc", ("gc_ms",), _total),
    ("total_task_count", "spark.stage.task_count", ("task_count",), _total),
)

# Kinds cujo subject e o JOB e nao o stage. No recorte de um stage a medida que
# vem deles nao esta AUSENTE -- ela nao existe ali --, entao ela sai fora de
# `bench.stage_delta` por construcao, e nao por falta de dado. Rateá-la entre os
# stages inventaria atribuicao que o event log nao da.
_JOB_SCOPED_KINDS = frozenset({"spark.job.spill_summary"})

_STAGE_MEASURES = tuple(m for m in _RUN_MEASURES if m[1] not in _JOB_SCOPED_KINDS)

# Estado de uma medida num lado. `partial` e `absent` sao os dois jeitos de nao
# ter a medida; so `usable` entra em `bench.run_delta`.
_USABLE = "usable"
_PARTIAL = "partial"
_ABSENT = "absent"


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
    tocar nas medidas inteiras -- byte e contagem de task continuam inteiros.

    Tres casas estabilizam a soma ate cerca de 1e12: acima disso o epsilon do
    float de 64 bits passa de 1e-3 e o arredondamento deixa de absorver a ordem
    das parcelas. Fora da faixa pratica com folga -- 1e12 ms de tempo de task
    somado sao uns 31 anos --, e escrito aqui para que ninguem precise refazer a
    conta para saber onde a garantia acaba.
    """
    if isinstance(value, float):
        return round(value, 3)
    return value


def _delta_pct(before: float, after: float) -> float | None:
    """Variacao relativa. `None` quando o lado ANTES e zero -- dividir por zero
    ali nao produz "infinito por cento", produz uma afirmacao sem sentido.

    Presuncao declarada: a formula pressupoe base NAO NEGATIVA. Com `before`
    negativo o sinal do percentual inverte, e uma subida sairia como queda. As
    cinco medidas de hoje satisfazem isso por construcao -- tempo, byte, GC e
    contagem de task sao nao negativos --, entao nao ha guarda aqui: guarda para
    caso inalcancavel e codigo que ninguem consegue provar. Medida nova que
    possa ser negativa (um saldo, um delta ja calculado) precisa reabrir esta
    decisao antes de entrar em `_RUN_MEASURES`.
    """
    if before == 0:
        return None
    return round((after - before) / before * 100, 1)


def _side_totals(facts: Sequence[Fact], spec: _MeasureSpec) -> dict[str, tuple[str, float, int]]:
    """Por medida: (estado deste lado, total somado, facts sem a chave).

    O total so vale quando o estado e `usable`. Em `partial` ele seria piso, e
    em `absent` ele seria zero inventado -- os dois ficam fora do delta.

    `spec` e `_RUN_MEASURES` no recorte do run e `_STAGE_MEASURES` no recorte de
    um simbolo; o resto e o MESMO caminho, de proposito. Um segundo caminho para
    o stage teria a mesma tabela de presenca escrita duas vezes, e a segunda
    copia so seria descoberta errada quando `SF-BENCH-002` acusasse regressao
    inexistente.
    """
    totals: dict[str, tuple[str, float, int]] = {}
    for name, kind, keys, combine in spec:
        complete = 0
        incomplete = 0
        total: float = 0
        for fact in facts:
            if fact.kind != kind:
                continue
            measures = fact.measures if isinstance(fact.measures, dict) else {}
            values = {key: _read(measures, key) for key in keys}
            if any(value is None for value in values.values()):
                incomplete += 1
                continue
            complete += 1
            total += combine({key: value for key, value in values.items() if value is not None})

        if complete == 0:
            status = _ABSENT
        elif incomplete:
            status = _PARTIAL
        else:
            status = _USABLE
        totals[name] = (status, _round(total), incomplete)
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


def _compare(
    before_totals: dict[str, tuple[str, float, int]],
    after_totals: dict[str, tuple[str, float, int]],
    spec: _MeasureSpec,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """As measures do delta e os furos que impediram cada uma.

    Um caminho so para o run e para o stage: as quatro formas de dizer "nao sei"
    do topo deste modulo valem no recorte de um simbolo tanto quanto no do run.
    """
    measures: dict[str, Any] = {}
    unresolved: list[dict[str, Any]] = []
    for name, _kind, keys, _combine in spec:
        before_status, before_value, before_missing = before_totals[name]
        after_status, after_value, after_missing = after_totals[name]

        if before_status == _USABLE:
            measures[f"{name}_before"] = before_value
        if after_status == _USABLE:
            measures[f"{name}_after"] = after_value

        unusable = [
            side
            for side, status in (("before", before_status), ("after", after_status))
            if status != _USABLE
        ]
        if not unusable:
            pct = _delta_pct(before_value, after_value)
            if pct is not None:
                measures[f"{name}_delta_pct"] = pct
            continue

        # Um lado parcial e um lado ausente sao problemas diferentes, e o
        # `reason` diz qual predomina: parcial e o mais traicoeiro dos dois,
        # porque ha numero somado ali -- so que ele e piso.
        if _PARTIAL in (before_status, after_status):
            reason = "measure_partial_keys"
        elif len(unusable) == 2:
            reason = "measure_absent_both_sides"
        else:
            reason = "measure_absent_one_side"

        unresolved.append(
            {
                "reason": reason,
                "sides": unusable,
                "measure": name,
                "keys": list(keys),
                "missing_key_fact_count": {"before": before_missing, "after": after_missing},
            }
        )
    return measures, unresolved


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


def _stage_ids(facts: Sequence[Fact]) -> list[str]:
    """Os `stage_id` distintos, em ordem numerica quando sao numero.

    Texto puro os ordenaria como `["10", "2"]` -- deterministico, mas ilegivel na
    evidencia de um achado. Id que nao e digito cai depois, ordenado como texto:
    ele nao vem de `event_log.py`, vem de um arquivo de facts editado a mao.
    """
    ids = [stage_id for stage_id, _symbol in _stage_keys(facts)]
    return sorted(ids, key=lambda s: (0, int(s), "") if s.isdigit() else (1, 0, s))


def _named_stage_groups(facts: Sequence[Fact]) -> dict[str, list[Fact]]:
    """Os facts de stage COM nome, agrupados por `symbol` -- a unidade do
    casamento. Facts de outro tipo de subject (o resumo de spill, que e do job)
    ficam de fora: eles nao pertencem a stage nenhum."""
    groups: dict[str, list[Fact]] = {}
    for fact in facts:
        subject = fact.subject if isinstance(fact.subject, dict) else {}
        if subject.get("type") != "stage":
            continue
        symbol = str(subject.get("symbol", ""))
        if not symbol:
            continue
        groups.setdefault(symbol, []).append(fact)
    return groups


def _nameless_stages(facts: Sequence[Fact]) -> list[dict[str, Any]]:
    """Um subject por stage SEM nome, deduplicado por `stage_id`.

    Cada um por si, e nao um grupo unico por lado: junta-los num fact so repetiria
    dentro do lado o erro que o casamento recusa entre os lados -- tratar como uma
    coisa stages que so tem em comum a falta de nome.
    """
    seen: dict[str, dict[str, Any]] = {}
    for fact in facts:
        subject = fact.subject if isinstance(fact.subject, dict) else {}
        if subject.get("type") != "stage" or str(subject.get("symbol", "")):
            continue
        seen.setdefault(str(subject.get("stage_id", "")), subject)
    return [seen[key] for key in sorted(seen)]


def _unmatched_subject(symbol: str, side: str, stage_id: Any = None) -> dict[str, Any]:
    """O lado entra no SUBJECT, nao so em `attrs`.

    `Fact.id` e sha1 de (kind, subject, measures) e ignora `attrs` (D-4a-2): sem
    o lado ali, o mesmo stage sem nome presente nos dois runs sairia com um id
    so, e um dos dois desapareceria da saida. `stage_id` entra so quando ele e a
    unica identidade que resta -- stage sem nome --, e aqui ele nao instabiliza
    nada, porque o fact afirma sobre UM lado, nao sobre o par.
    """
    subject: dict[str, Any] = {"type": "stage", "symbol": f"{symbol}#{side}"}
    if isinstance(stage_id, int) and not isinstance(stage_id, bool) and stage_id >= 0:
        subject["stage_id"] = stage_id
    return subject


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

    measures, unresolved = _compare(
        _side_totals(before, _RUN_MEASURES),
        _side_totals(after, _RUN_MEASURES),
        _RUN_MEASURES,
    )

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

    before_groups = _named_stage_groups(before)
    after_groups = _named_stage_groups(after)
    matched_stages = 0
    unmatched_stages = 0

    for symbol in sorted(set(before_groups) & set(after_groups)):
        before_stages = before_groups[symbol]
        after_stages = after_groups[symbol]
        before_ids = _stage_ids(before_stages)
        after_ids = _stage_ids(after_stages)
        matched_stages += len(before_ids) + len(after_ids)

        # O furo de medida no recorte de um simbolo NAO vira `bench.unresolved`:
        # o furo e da comparacao, e o `bench.unresolved` do run ja o nomeou uma
        # vez. Repeti-lo por simbolo daria ruido proporcional ao numero de
        # stages -- dezenas de facts dizendo a mesma coisa, afogando o resto da
        # saida. A chave simplesmente falta no delta, que e como este motor diz
        # "nao sei", e `engine._where_matches` reprova caminho ausente.
        stage_measures, _ = _compare(
            _side_totals(before_stages, _STAGE_MEASURES),
            _side_totals(after_stages, _STAGE_MEASURES),
            _STAGE_MEASURES,
        )
        stage_measures["before_stage_count"] = len(before_ids)
        stage_measures["after_stage_count"] = len(after_ids)

        out.append(
            Fact(
                kind="bench.stage_delta",
                # Sem `stage_id`: ele difere entre os runs e entraria no
                # `Fact.id`, fazendo a identidade do delta -- que um
                # `benchmark_ref` cita -- depender de um numero instavel.
                subject={"type": "stage", "symbol": symbol},
                measures=stage_measures,
                attrs={"before_stage_ids": before_ids, "after_stage_ids": after_ids},
                provenance=provenance,
            )
        )

    for side, groups, other in (
        ("before", before_groups, after_groups),
        ("after", after_groups, before_groups),
    ):
        for symbol in sorted(set(groups) - set(other)):
            stage_ids = _stage_ids(groups[symbol])
            unmatched_stages += len(stage_ids)
            out.append(
                Fact(
                    kind="bench.unmatched",
                    subject=_unmatched_subject(symbol, side),
                    measures={"stage_count": len(stage_ids)},
                    attrs={
                        "reason": "symbol_absent_on_other_side",
                        "side": side,
                        "symbol": symbol,
                        "stage_ids": stage_ids,
                    },
                    provenance=provenance,
                )
            )

    for side, source in (("before", before), ("after", after)):
        for subject in _nameless_stages(source):
            unmatched_stages += 1
            out.append(
                Fact(
                    kind="bench.unmatched",
                    subject=_unmatched_subject("", side, subject.get("stage_id")),
                    measures={"stage_count": 1},
                    attrs={
                        "reason": "empty_symbol",
                        "side": side,
                        "symbol": "",
                        "stage_ids": [str(subject.get("stage_id", ""))],
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
    # Os quatro contadores sao de STAGE -- subject `(stage_id, symbol)` distinto
    # --, e nao de simbolo nem de fact emitido: `matched + unmatched` fecha
    # exatamente `before + after`, entao nenhum stage cai fora da conta. Quantos
    # deltas sairam se conta pelos proprios `bench.stage_delta`; o que so a
    # sentinela responde e QUANTO da comparacao esta coberto.
    out.append(
        Fact(
            kind="bench.analyzed",
            subject=_run_subject(path_hint),
            measures={
                "matched_stage_count": matched_stages,
                "unmatched_stage_count": unmatched_stages,
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

    for attrs in unresolved:
        out.append(
            Fact(
                kind="bench.unresolved",
                subject=_unresolved_subject(path_hint, str(attrs["measure"])),
                attrs=attrs,
                provenance=provenance,
            )
        )

    unknown = {f.kind for f in out} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(out)
