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

Cinco formas de dizer "nao sei", nenhuma delas zero:

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
  * medida que um simbolo CASADO tem num lado so tambem produz piso, e essa e a
    forma que `_side_totals` sozinho nao enxerga: ele afere presenca dentro dos
    facts que existem, nunca por stage que deveria ter contribuido. Sai o
    `_delta_pct` daquela medida do `bench.run_delta` -- so o percentual, nunca os
    totais, que foram observados -- mais um `bench.unresolved` nomeando simbolo e
    medida. Simbolo NAO casado nao entra nessa conta: stage que sumiu entre os
    runs e mudanca de trabalho, que e o que o benchmark existe para relatar, e
    `bench.unmatched` ja o nomeia.

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
        "bench.runtime_pair",
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

# Kinds cujo subject e o JOB e nao o stage: rateá-los entre os stages inventaria
# atribuicao que o event log nao da. So `spark.job.spill_summary` esta nessa
# situacao, e ele NAO e a unica fonte de spill -- `event_log.py:236` emite
# `spark.stage.spill` por stage, e o proprio resumo do job e a soma dele
# (`event_log.py:528-544`). Entao o recorte de stage tem spill: mesma medida,
# mesma unidade, outra granularidade de fonte. O nome da chave e o mesmo nos dois
# recortes de proposito -- `SF-BENCH-003` ("mais rapido mas derramando") le
# `total_spill_bytes` sem precisar saber de qual fact veio.
_JOB_SCOPED_KINDS = frozenset({"spark.job.spill_summary"})

_STAGE_MEASURES: _MeasureSpec = tuple(
    m for m in _RUN_MEASURES if m[1] not in _JOB_SCOPED_KINDS
) + (
    (
        "total_spill_bytes",
        "spark.stage.spill",
        ("memory_spill_bytes", "disk_spill_bytes"),
        _total,
    ),
)

# Estado de uma medida num lado. `partial` e `absent` sao os dois jeitos de nao
# ter a medida; so `usable` entra em `bench.run_delta`.
_USABLE = "usable"
_PARTIAL = "partial"
_ABSENT = "absent"


def _run_subject(path_hint: str) -> dict[str, Any]:
    return {"type": "job_run", "symbol": path_hint or "benchmark"}


def _job_run_subject(path_hint: str, detail: str) -> dict[str, Any]:
    """Subject proprio por `detail`. `Fact.id` e sha1 de (kind, subject,
    measures) -- `attrs` fica FORA --, entao dois facts do mesmo kind com o
    mesmo subject e sem measures teriam o mesmo id e seriam indistinguiveis na
    saida.

    Chamava-se `_unresolved_subject` ate `bench.runtime_pair` existir. O nome
    antigo descrevia o unico chamador da epoca, nao o que a funcao faz -- e um
    nome que descreve o chamador envelhece no segundo chamador."""
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

    Um caminho so para o run e para o stage: as formas de dizer "nao sei" do topo
    deste modulo valem no recorte de um simbolo tanto quanto no do run. E o
    recorte de simbolo devolve mais do que measures: os furos dele sao a UNICA
    forma de ver a quinta -- medida que existe num lado so de um simbolo casado --,
    que no recorte do run e invisivel por construcao.
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


def _nameless_stages(facts: Sequence[Fact]) -> list[str]:
    """O `stage_id` de cada stage SEM nome, como texto e deduplicado.

    Cada um por si, e nao um grupo unico por lado: junta-los num fact so repetiria
    dentro do lado o erro que o casamento recusa entre os lados -- tratar como uma
    coisa stages que so tem em comum a falta de nome.
    """
    seen: set[str] = set()
    for fact in facts:
        subject = fact.subject if isinstance(fact.subject, dict) else {}
        if subject.get("type") != "stage" or str(subject.get("symbol", "")):
            continue
        seen.add(str(subject.get("stage_id", "")))
    return sorted(seen)


def _nameless_subject(side: str, stage_id: str) -> dict[str, Any]:
    """Subject do stage SEM nome: lado e `stage_id` dentro do `symbol`.

    `Fact.id` e sha1 de (kind, subject, measures) e ignora `attrs` (D-4a-2): sem
    lado e sem id ali, dois stages sem nome sairiam com o mesmo id e um deles
    desapareceria da saida.

    Por que nao a chave `stage_id` do subject: o schema exige inteiro >= 0
    (`fact.schema.json`), e o `stage_id` de um ARQUIVO de facts nao e
    necessariamente inteiro -- `_facts_from_dicts` copia o subject verbatim.
    Guardar so quando fosse inteiro deixaria o caso nao numerico sem identidade
    nenhuma, que e a colisao de volta; guardar sempre como texto reprovaria no
    `validate_fact`. O `symbol` aceita os dois, e `attrs["stage_ids"]` mantem o
    valor legivel.

    Aqui o `stage_id` nao instabiliza nada -- ao contrario de
    `bench.stage_delta`, este fact afirma sobre UM lado, nao sobre o par.

    Simbolo NOMEADO nao passa por aqui: ele aparece num lado so por construcao,
    entao nao ha colisao para resolver, e `"join#before"` no subject seria
    mutilacao sem ganho.
    """
    return {"type": "stage", "symbol": f"#{side}#{stage_id}"}


def _runtime_pair_facts(
    before_runtime: str,
    after_runtime: str,
    path_hint: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    """O eixo de runtime da comparacao, ou o que falta para ele existir.

    Separado de `build_benchmark` porque a resposta aqui nao depende de nenhuma
    medida: ela depende so do que foi DECLARADO sobre as duas execucoes. Manter
    os dois juntos misturaria "o que eu medi" com "sobre o que eu fui
    informado", e sao coisas de procedencia diferente.
    """
    if not before_runtime and not after_runtime:
        # Ninguem perguntou sobre runtime. Emitir `missing_runtime_label` aqui
        # diria que falta algo numa comparacao que nao pediu esse eixo -- e uma
        # comparacao entre duas execucoes no MESMO runtime continua valendo,
        # que e o caso de medir uma mudanca de codigo.
        return []

    faltando = [
        lado
        for lado, valor in (("before", before_runtime), ("after", after_runtime))
        if not valor
    ]
    if faltando:
        return [
            Fact(
                kind="bench.unresolved",
                subject=_job_run_subject(path_hint, "missing_runtime_label"),
                attrs={
                    "reason": "missing_runtime_label",
                    "sides": faltando,
                    "measure": "",
                },
                provenance=provenance,
            )
        ]
    if before_runtime == after_runtime:
        return [
            Fact(
                kind="bench.unresolved",
                subject=_job_run_subject(path_hint, "same_runtime_label"),
                attrs={
                    "reason": "same_runtime_label",
                    "sides": ["before", "after"],
                    "measure": "",
                    "runtime": before_runtime,
                },
                provenance=provenance,
            )
        ]
    return [
        Fact(
            kind="bench.runtime_pair",
            # `job_run`, e nao um `type` novo: o vocabulario de subject e
            # FECHADO pelo schema, e o fato afirma sobre o PAR de execucoes --
            # que e o que `job_run` ja nomeia nos outros `bench.*`. O par de
            # runtimes entra no `symbol` porque `Fact.id` e sha de (kind,
            # subject, measures) e `attrs` fica de fora: sem ele, dois pares
            # diferentes teriam o mesmo id.
            subject=_job_run_subject(path_hint, f"{before_runtime}..{after_runtime}"),
            attrs={"before_runtime": before_runtime, "after_runtime": after_runtime},
            provenance=provenance,
        )
    ]


def build_benchmark(
    before: Sequence[Fact],
    after: Sequence[Fact],
    path_hint: str = "",
    before_runtime: str = "",
    after_runtime: str = "",
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

    `before_runtime` e `after_runtime` (secao 52) rotulam em QUE runtime cada
    execucao rodou. Sao OPCIONAIS porque a comparacao entre duas execucoes no
    mesmo runtime continua valendo -- e o caso de medir uma mudanca de codigo.
    O que eles acrescentam e a unica coisa que transforma um benchmark em prova
    de migracao: `bench.runtime_pair` diz que os dois lados sao runtimes
    DIFERENTES, e nomeia quais.

    Tres respostas, e as tres sao declaradas em vez de silenciosas:

      - Os dois rotulos, e diferentes -> `bench.runtime_pair`. E o unico caso
        que sustenta uma afirmacao sobre migracao.
      - Os dois rotulos, e iguais -> `bench.unresolved` com
        `same_runtime_label`. Comparar um runtime consigo mesmo nao prova nada
        sobre trocar de runtime, e deixar isso passar como benchmark de
        migracao e a forma barata de produzir um numero que ninguem pode usar.
      - Um rotulo so -> `bench.unresolved` com `missing_runtime_label`,
        nomeando o lado que falta. Os deltas continuam saindo: o que fica sem
        lastro e o EIXO de runtime, nao a comparacao.
      - Nenhum rotulo -> nada. Ninguem perguntou sobre runtime, e responder
        "falta" a uma pergunta que nao foi feita e ruido, nao honestidade.
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
                subject=_job_run_subject(path_hint, "missing_log_analyzed"),
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

    before_groups = _named_stage_groups(before)
    after_groups = _named_stage_groups(after)
    matched_stages = 0
    unmatched_stages = 0
    # Medidas cujo total de run soma populacoes diferentes dos dois lados -- ver
    # o bloco de `measure_absent_for_matched_symbol` abaixo. O casamento roda
    # ANTES de `bench.run_delta` ser emitido justamente para que ele possa tirar
    # de la o percentual que essas medidas fabricariam.
    fabricated: set[str] = set()

    matched_symbols = sorted(set(before_groups) & set(after_groups))
    for symbol in matched_symbols:
        before_stages = before_groups[symbol]
        after_stages = after_groups[symbol]
        before_ids = _stage_ids(before_stages)
        after_ids = _stage_ids(after_stages)
        matched_stages += len(before_ids) + len(after_ids)

        stage_measures, holes = _compare(
            _side_totals(before_stages, _STAGE_MEASURES),
            _side_totals(after_stages, _STAGE_MEASURES),
            _STAGE_MEASURES,
        )
        stage_attrs: dict[str, Any] = {
            "before_stage_ids": before_ids,
            "after_stage_ids": after_ids,
        }

        # Populacao de stages diferente: dois `scan` antes contra um depois, com
        # o mesmo custo em cada um, daria -50% -- queda de trabalho por stage que
        # ninguem observou. Em todo outro caso onde a comparacao nao se sustenta
        # (chave parcial, medida de um lado so, base zero) este modulo OMITE o
        # `_delta_pct`; aqui nao seria diferente. Os totais ficam, porque foram
        # observados; a razao da omissao vai em `attrs`, para a chave nao sumir
        # sem explicacao.
        if len(before_ids) != len(after_ids):
            for key in [k for k in stage_measures if k.endswith("_delta_pct")]:
                del stage_measures[key]
            stage_attrs["delta_pct_omitted"] = "stage_count_changed"

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
                attrs=stage_attrs,
                provenance=provenance,
            )
        )

        # Medida que existe num lado do simbolo CASADO e some no outro.
        #
        # `_side_totals` afere presenca dentro dos facts que EXISTEM, nunca por
        # stage que deveria ter contribuido: se um simbolo casado perde o fact de
        # gc no depois, o lado depois continua `usable` e o total do run cai --
        # regressao ao contrario, melhora fabricada, o mesmo defeito que a Task 1
        # fechou para a chave parcial. O recorte de simbolo e o unico lugar onde
        # isso e visivel, e ele so existe a partir do casamento desta task.
        #
        # Ausencia dos DOIS lados nao entra: ali nao ha piso contra total, nao ha
        # o que fabricar. O furo por SIMBOLO NAO CASADO tambem nao, porque
        # `bench.unmatched` ja o nomeia.
        for hole in holes:
            if len(hole["sides"]) != 1:
                continue
            fabricated.add(str(hole["measure"]))
            unresolved.append(
                {
                    **hole,
                    "reason": "measure_absent_for_matched_symbol",
                    "symbol": symbol,
                }
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
                    subject={"type": "stage", "symbol": symbol},
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
        for stage_id in _nameless_stages(source):
            unmatched_stages += 1
            out.append(
                Fact(
                    kind="bench.unmatched",
                    subject=_nameless_subject(side, stage_id),
                    measures={"stage_count": 1},
                    attrs={
                        "reason": "empty_symbol",
                        "side": side,
                        "symbol": "",
                        "stage_ids": [stage_id],
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
    # `bench.run_delta`, ja sabendo quais medidas somam populacoes diferentes.
    #
    # O percentual SAI quando um simbolo casado tem a medida num lado so: ali o
    # total do lado furado e PISO, e piso contra total fabrica melhora -- a mesma
    # decisao que a Task 1 tomou para chave parcial e para base zero. Os totais
    # ficam, porque foram observados; o que nao se sustenta e a razao entre eles,
    # e `bench.unresolved` nomeia simbolo e medida.
    #
    # Simbolo NAO CASADO nao entra nesta conta, e a assimetria e deliberada:
    # stage que sumiu entre os runs e mudanca de TRABALHO -- a verdade que o
    # benchmark existe para relatar --, enquanto simbolo casado sem a medida num
    # lado e mudanca de MEDICAO. O primeiro o operador quer ver como percentual;
    # o segundo e um numero que ninguem observou.
    #
    # Ruido medido: ZERO. As duas fixtures de `fixtures/eventlog/` nas quatro
    # combinacoes nao produzem um furo sequer, e nenhum `_delta_pct` do run cai.
    # Nao e sorte: `event_log.py` co-emite os kinds de stage para todo stage
    # analisado (inclusive `spark.stage.spill` com zero byte, `event_log.py:516`),
    # entao dois lados vindos do extrator tem sempre os mesmos kinds por simbolo.
    # O furo so e alcancavel pelo ARQUIVO de facts do verbo `benchmark` -- que e
    # exatamente onde a fabricacao e real (mesmo argumento do D-4a-6).
    for name in sorted(fabricated):
        measures.pop(f"{name}_delta_pct", None)

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

    # Os quatro `*_stage_count` sao de STAGE -- subject `(stage_id, symbol)`
    # distinto --, e nao de simbolo: `matched + unmatched` fecha exatamente
    # `before + after`, entao nenhum stage cai fora da conta.
    #
    # `stage_delta_count` conta FACT emitido, e existe porque os dois numeros
    # divergem quando um simbolo tem varios stages -- tres stages casados podem
    # sair em um delta so, e ler `matched_stage_count` como "quantos deltas" e o
    # erro facil. Contar os `bench.stage_delta` da saida nao substitui: o verbo
    # `benchmark` pagina (`_facts_page`), e uma pagina nao e o total.
    out.append(
        Fact(
            kind="bench.analyzed",
            subject=_run_subject(path_hint),
            measures={
                "matched_stage_count": matched_stages,
                "unmatched_stage_count": unmatched_stages,
                "stage_delta_count": len(matched_symbols),
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
        # O detalhe inclui o simbolo quando ha um: o furo de `total_gc_ms` do run
        # e o furo de `total_gc_ms` do simbolo `y` sao dois fatos diferentes, e
        # sem isso teriam o mesmo subject, as mesmas measures (nenhuma) e o mesmo
        # `Fact.id`.
        symbol = str(attrs.get("symbol", ""))
        detail = f"{symbol}#{attrs['measure']}" if symbol else str(attrs["measure"])
        out.append(
            Fact(
                kind="bench.unresolved",
                subject=_job_run_subject(path_hint, detail),
                attrs=attrs,
                provenance=provenance,
            )
        )

    out.extend(_runtime_pair_facts(before_runtime, after_runtime, path_hint, provenance))

    unknown = {f.kind for f in out} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(out)
