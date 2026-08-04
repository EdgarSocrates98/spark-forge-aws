# SparkForge Fase 4a — benchmark antes/depois: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dar produtor ao gate que rejeita ganho sem `benchmark_ref`, comparando dois conjuntos de facts de event log que o motor já sabe extrair.

**Architecture:** `sparkforge/facts/benchmark.py` é função pura sobre `Fact`s, no padrão de `call_graph.py` — nunca lê artefato bruto, nunca executa Spark. Ele decide a comparação porque `engine._condition_candidates` avalia um fact por vez; o catálogo lê atributo de um fact só.

**Tech Stack:** Python stdlib, YAML declarativo, pytest.

**Spec:** [`../specs/2026-08-03-sparkforge-fase4a-benchmark-design.md`](../specs/2026-08-03-sparkforge-fase4a-benchmark-design.md) — §7 são os nove critérios.

---

## Fatos do ambiente verificados antes de escrever este plano

```
event_log.py emite, e é TUDO que o comparador tem:
  spark.log_analyzed      subj source_location  line_count event_count unresolved_count
  spark.job.spill_summary subj job_run    stages_with_spill total_memory_spill_bytes
                                          total_disk_spill_bytes
  spark.cluster.cores     subj job_run    available_cores executor_count
  spark.stage.task_duration subj stage    min_ms p50_ms p95_ms max_ms mean_ms task_count
  spark.stage.task_input    subj stage    min_bytes p50_bytes p95_bytes max_bytes total_bytes
  spark.stage.spill         subj stage    memory_spill_bytes disk_spill_bytes input_bytes
  spark.stage.gc            subj stage    gc_ms executor_run_ms
  spark.stage.task_count    subj stage    task_count available_cores
  spark.executor.memory_usage / spark.executor.lost / spark.runtime_version / spark.unresolved

subject de stage: {"type":"stage","symbol":"stage_uniform_scan","stage_id":0}
Fact.id = "f_" + sha1(canonical({kind, subject, measures}))[:6]   -- attrs FORA
validate_finding(payload)  recebe SO o achado; nao tem o conjunto de facts
CLI de modulo derivado: `analyze call-graph --facts <arquivo> --out`
```

**A consequência que decide a Task 1: não existe fact de duração de relógio.**
Duração vive por stage, em `task_duration`. O total honesto é **tempo de task somado** (`mean_ms × task_count`, somado sobre os stages) — que é *trabalho*, não *tempo decorrido*. Um job pode ficar mais rápido no relógio e somar mais tempo de task, ao paralelizar melhor. O measure **tem que se chamar `total_task_ms`**, e a `explanation` da regra tem que dizer isso. Chamá-lo de `duration_ms` seria o defeito que a 5b corrigiu em `unreachable_function_count`: nome que promete mais do que entrega.

**A consequência que decide a Task 6:** `validate_finding` não vê os facts, então "o `benchmark_ref` aponta para um `bench.run_delta` que existe" **não é verificável** na assinatura de hoje. A Task 6 valida em duas camadas: forma sempre, pertinência quando o conjunto de facts for passado.

---

## File Structure

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/benchmark.py` | compara dois conjuntos de facts e emite `bench.*` |
| `rules/catalog/benchmark.yaml` | área `SF-BENCH` |
| `tests/test_facts_benchmark.py` | o comparador |
| `tests/test_fixtures_golden_bench.py` | golden do domínio |
| `fixtures/bench/*` | seis casos, cada um com **dois** event logs |

**Modificados:** `sparkforge/findings/validate.py`, `sparkforge/adapters/{cli,_core,tools}.py`, as duas listas `EXTRACTORS`, as três listas de `tests/test_adapters_tools.py`, `parity.yaml`, `manifest.json`, `scripts/regen_fixtures.py`, `agents/spark-performance-architect.md`, `skills/benchmark-pyspark-job/SKILL.md`, `docs/superpowers/STATUS.md`.

---

## Task 1: o comparador — totais do run

**Files:**
- Create: `sparkforge/facts/benchmark.py`, `tests/test_facts_benchmark.py`

- [x] **Step 1: Escreva o teste que falha**

```python
# tests/test_facts_benchmark.py
from sparkforge.facts.benchmark import EMITTED_KINDS, build_benchmark
from sparkforge.findings.models import Fact


def _stage(symbol: str, stage_id: int, **measures) -> Fact:
    return Fact(
        kind="spark.stage.task_duration",
        subject={"type": "stage", "symbol": symbol, "stage_id": stage_id},
        measures={"mean_ms": measures.get("mean_ms", 100), "task_count": measures.get("task_count", 10)},
        provenance={"artifact": measures.get("artifact", "a.jsonl"), "extractor": "event_log@0.1.0"},
    )


def _analyzed(artifact: str) -> Fact:
    return Fact(
        kind="spark.log_analyzed",
        subject={"type": "source_location", "file": artifact, "line": 0, "col": 0, "symbol": "", "snippet": ""},
        measures={"line_count": 10, "event_count": 10, "unresolved_count": 0},
        provenance={"artifact": artifact, "extractor": "event_log@0.1.0"},
    )


def test_o_total_de_tempo_de_task_e_somado_dos_dois_lados():
    before = [_analyzed("a.jsonl"), _stage("scan", 0, mean_ms=200, task_count=10)]
    after = [_analyzed("b.jsonl"), _stage("scan", 0, mean_ms=100, task_count=10)]

    facts = build_benchmark(before, after)

    delta = [f for f in facts if f.kind == "bench.run_delta"][0]
    assert delta.measures["total_task_ms_before"] == 2000
    assert delta.measures["total_task_ms_after"] == 1000
    assert delta.measures["total_task_ms_delta_pct"] == -50.0


def test_um_lado_sem_log_analyzed_vira_unresolved():
    facts = build_benchmark([_analyzed("a.jsonl")], [])
    assert [f.kind for f in facts if f.kind == "bench.unresolved"] == ["bench.unresolved"]
    assert [f for f in facts if f.kind == "bench.run_delta"] == []


def test_o_namespace_declarado_cobre_os_cinco_kinds():
    assert EMITTED_KINDS == {
        "bench.run_delta",
        "bench.stage_delta",
        "bench.unmatched",
        "bench.analyzed",
        "bench.unresolved",
    }
```

- [x] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_facts_benchmark.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sparkforge.facts.benchmark'`
Medido: exatamente isso, na coleta do módulo.

- [x] **Step 3: Implemente o mínimo**

> **Cinco desvios medidos contra o esqueleto abaixo.**
>
> **D-4a-1 — `DERIVER_ID` virou `EXTRACTOR_ID`.** Os **quatorze** módulos
> pré-existentes de `sparkforge/facts/` — quinze com este, medido por
> `grep -rl "^EXTRACTOR_ID" sparkforge/facts/` —, inclusive os dois derivados
> (`call_graph.py`, `fusion.py`), declaram `EXTRACTOR_ID`, e
> `tests/test_facts_fusion.py` e `tests/test_facts_catalog_schema.py` asseguram o
> prefixo por esse nome. Um nome só para este módulo seria diferença sem
> diferença.
>
> **D-4a-2 — `bench.unresolved` precisa de subject próprio por motivo.**
> `Fact.id` é sha1 de `(kind, subject, measures)` e **`attrs` fica de fora**: os
> cinco unresolved de medida ausente têm o mesmo subject e nenhuma measure, então
> sairiam todos com o **mesmo id**, indistinguíveis na saída e no `evidence` de um
> achado. `_unresolved_subject` ancora em `"<hint>#<detalhe>"`. Há teste.
>
> **D-4a-3 — medida ausente de UM lado é caso próprio.** O plano só previa
> ausência dos dois lados. Preencher o lado que falta com zero afirmaria uma queda
> (ou uma subida) que ninguém observou — é o "nunca zero" do §8 do spec. Sai o
> valor do lado que tem, **sem** `_delta_pct`, mais um `bench.unresolved` com
> `reason: "measure_absent_one_side"` e o lado que faltou.
>
> **D-4a-4 — `before_artifact` virou `before_artifacts`, lista ordenada e
> deduplicada.** Não há exatamente um `spark.log_analyzed` por lado: event log
> rolante (`spark.eventLog.rolling.enabled`) e extração de vários arquivos
> produzem vários. Pegar o primeiro esconderia os outros. A coleta é `set` e
> depois `sorted`: dois `spark.log_analyzed` do **mesmo** artefato aparecem uma
> vez só — a lista responde "de que arquivos este lado veio", não "quantos facts
> sentinela havia".
>
> **D-4a-5 — totais passam por `_round`.** `mean_ms` é média (`sum/n`), então
> `mean_ms * task_count` carrega ruído de ponto flutuante que entraria no
> `Fact.id` e faria o golden depender de bit de arredondamento. Arredonda só o que
> é `float`; byte e contagem de task continuam inteiros. A revisão mediu um efeito
> que eu não tinha alegado: sob 300 permutações da ordem de entrada de 60 stages,
> o `Fact.id` fica único — o arredondamento também absorve a **não
> associatividade** da soma de float. Três casas valem até ~1e12 (≈31 anos de
> tempo de task somado); acima disso o eps do float de 64 bits passa de 1e-3, e o
> limite está escrito no docstring de `_round`.
>
> **D-4a-6 (revisão da Task 1) — presença é por CHAVE, não por kind.** Medido pelo
> revisor: `spark.stage.task_duration` **sem** `task_count` dava
> `total_task_ms_before = 0` e nenhum `bench.unresolved`, contradizendo o
> docstring do próprio módulo. Hoje é inalcançável, porque `event_log.py:204-211`
> co-emite as chaves — **a Task 3 o torna alcançável**, porque o verbo `benchmark`
> lê facts de um *arquivo*, que alguém edita e que outra ferramenta gera. Mesmo
> raciocínio da colisão de `Fact.id` (D-4a-2): barato agora, caro depois das
> fixtures.
>
> Cada medida declara as chaves que exige (`_RUN_MEASURES`), e um fact do kind sem
> todas elas não contribui. Daí três estados por lado: `usable`, `absent` (nenhum
> fact completo) e `partial` (uns completos, outros não). **Parcial também é
> ausência**, com `reason: "measure_partial_keys"` e
> `missing_key_fact_count`: somar só os completos produziria um **piso**, e piso
> de um lado contra total do outro *fabrica melhora* — `SF-BENCH-002` acusaria
> regressão inexistente, ou calaria uma real. Errar para o silêncio é o lado certo
> aqui. Valor não numérico (`"400"`, `True`) conta como chave ausente.
>
> **Ruído medido: zero.** As duas fixtures de `fixtures/eventlog/` comparadas nas
> quatro combinações não produzem um `bench.unresolved` sequer, e as cinco medidas
> saem completas — a única chave omitida é `total_spill_bytes_delta_pct` quando o
> lado antes não derramou, que é a regra de divisão por zero funcionando.
>
> **D-4a-7 — a presunção de base não negativa, escrita e sem guarda.** Com
> `before` negativo o sinal de `_delta_pct` inverte, e uma subida sairia como
> −120%. Inalcançável pelas cinco medidas de hoje (tempo, byte, GC e contagem são
> não negativos), então **não há guarda** — guarda para caso inalcançável é código
> que ninguém consegue provar. A presunção está no docstring de `_delta_pct`, com
> a condição de reabertura: medida nova que possa ser negativa reabre a decisão
> antes de entrar em `_RUN_MEASURES`. Presunção escrita é decisão; presunção
> silenciosa é acidente esperando fact novo.

```python
# sparkforge/facts/benchmark.py
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
relogio no event log lido: `event_log.py` emite duracao por stage e nada de
wall-clock. Um job pode terminar antes no relogio e somar MAIS tempo de task, se
passou a paralelizar melhor. Chamar isso de `duration_ms` seria o defeito que a
Fase 5b corrigiu em `unreachable_function_count` -- nome que promete mais do que
entrega -- e aqui o preco seria maior, porque a regra que le a medida acusa
regressao.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

DERIVER_ID = "benchmark@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "bench.run_delta",
        "bench.stage_delta",
        "bench.unmatched",
        "bench.analyzed",
        "bench.unresolved",
    }
)


def _run_subject(path_hint: str) -> dict[str, Any]:
    return {"type": "job_run", "symbol": path_hint or "benchmark"}


def _delta_pct(before: float, after: float) -> float | None:
    """Variacao relativa. `None` quando o lado ANTES e zero -- dividir por zero
    ali nao produz "infinito por cento", produz uma afirmacao sem sentido."""
    if before == 0:
        return None
    return round((after - before) / before * 100, 1)


def _total_task_ms(facts: Sequence[Fact]) -> float:
    total = 0.0
    for fact in facts:
        if fact.kind != "spark.stage.task_duration":
            continue
        total += fact.measures.get("mean_ms", 0) * fact.measures.get("task_count", 0)
    return total


def _artifact_of(facts: Sequence[Fact]) -> str:
    for fact in facts:
        if fact.kind == "spark.log_analyzed":
            return str(fact.provenance.get("artifact", ""))
    return ""


def build_benchmark(
    before: Sequence[Fact], after: Sequence[Fact], path_hint: str = ""
) -> list[Fact]:
    provenance = {
        "artifact": path_hint,
        "artifact_sha256": "",
        "extractor": DERIVER_ID,
    }
    facts: list[Fact] = []

    missing = [
        side
        for side, source in (("before", before), ("after", after))
        if not any(f.kind == "spark.log_analyzed" for f in source)
    ]
    if missing:
        facts.append(
            Fact(
                kind="bench.unresolved",
                subject=_run_subject(path_hint),
                attrs={"reason": "missing_log_analyzed", "sides": missing},
                provenance=provenance,
            )
        )
        return sort_facts(facts)

    before_ms, after_ms = _total_task_ms(before), _total_task_ms(after)
    measures: dict[str, Any] = {
        "total_task_ms_before": before_ms,
        "total_task_ms_after": after_ms,
    }
    pct = _delta_pct(before_ms, after_ms)
    if pct is not None:
        measures["total_task_ms_delta_pct"] = pct

    facts.append(
        Fact(
            kind="bench.run_delta",
            subject=_run_subject(path_hint),
            measures=measures,
            attrs={"before_artifact": _artifact_of(before), "after_artifact": _artifact_of(after)},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)
```

- [x] **Step 4: Rode e veja passar**

Run: `python -m pytest tests/test_facts_benchmark.py -v`
Expected: PASS, 3 testes
Medido: PASS. São 19 testes ao fim da task, não 3 — os Steps 5 e 6 entram no mesmo arquivo.

- [x] **Step 5: As outras quatro medidas do run**

Teste primeiro, com a mesma forma do Step 1: `total_input_bytes` (soma de `spark.stage.task_input.total_bytes`), `total_spill_bytes` (de `spark.job.spill_summary`, somando memória e disco), `total_gc_ms` (soma de `spark.stage.gc.gc_ms`) e `total_task_count` (soma de `spark.stage.task_count.task_count`).

Cada uma sai com sufixo `_before`, `_after` e `_delta_pct`, e o `_delta_pct` é **omitido** quando o lado antes é zero — a chave ausente é como este motor diz "não sei", e `engine._where_matches` reprova caminho ausente, então a regra não avalia. Medida ausente dos **dois** lados vira `bench.unresolved` com `reason: "measure_absent_both_sides"` e o nome da medida em `attrs`.

> **A presença é por kind, não por valor** (medido no Step 5): `total_task_count`
> vem de `spark.stage.task_count` e não do `task_count` que
> `spark.stage.task_duration` também carrega — o primeiro conta as tasks
> declaradas pelo stage, o segundo conta as amostras de duração que o log trouxe.
> Confundi-los somaria a mesma medida por duas definições diferentes.

- [x] **Step 6: `bench.analyzed`, a sentinela**

`measures`: `matched_stage_count`, `unmatched_stage_count` (zero até a Task 2), `before_stage_count`, `after_stage_count`. `attrs`: os dois artefatos. Ela prova que a comparação rodou — sem ela, "nenhum achado" e "nunca comparei" ficam indistinguíveis.

Contagem de stage por lado é de **subjects distintos** `(stage_id, symbol)`, não de facts: cinco kinds descrevem o mesmo stage.

- [x] **Step 7: Commit**

```bash
git add sparkforge/facts/benchmark.py tests/test_facts_benchmark.py
git commit -m "feat(facts): comparador de duas execucoes, com o total que nao mente"
```

---

## Task 2: casamento de stage, estrito

**Files:**
- Modify: `sparkforge/facts/benchmark.py`, `tests/test_facts_benchmark.py`

- [x] **Step 1: Teste primeiro**

> **Três desvios medidos contra os testes e o esqueleto desta task.**
>
> **D-4a-8 — `matched_stage_count` conta STAGE, não par casado: 2 e não 1 no
> teste do Step 1.** O plano assertava `matched_stage_count == 1` e
> `unmatched_stage_count == 2` no mesmo par, e as duas chaves passariam a contar
> unidades diferentes — a primeira, casamentos; a segunda, stages —, com nome
> idêntico. Medido: `before_stage_count` e `after_stage_count`, que a Task 1 já
> emitia, contam subjects `(stage_id, symbol)` distintos; sob a leitura do plano
> nada fecha, e a pergunta "quanto da comparação está coberto por delta de stage"
> fica sem resposta. Sob a leitura de stage, `matched + unmatched ==
> before + after` **exatamente**, e há teste da identidade. Quantos deltas saíram
> continua respondível contando os próprios `bench.stage_delta` — a sentinela não
> precisa duplicar isso. É a disciplina de `opaque_caller_function_count` da Fase
> 5b feita aritmética: nenhum stage cai fora da conta.
>
> **D-4a-9 — o lado entra no *subject* de `bench.unmatched`.** `Fact.id` é sha1
> de (kind, subject, measures) e ignora `attrs` (D-4a-2 de novo). Dois stages sem
> nome com o mesmo `stage_id`, um em cada run, sairiam com o **mesmo id** se o
> lado vivesse só em `attrs` — e um dos dois desapareceria da saída. O subject é
> `{"type": "stage", "symbol": "<symbol>#<side>"}`, mesma forma de
> `_unresolved_subject`; `attrs["symbol"]` guarda o símbolo limpo, que é o que o
> teste do plano já lia. `stage_id` entra no subject **só** para stage sem nome,
> onde é a única identidade que resta — e ali ele não instabiliza nada, porque o
> fact afirma sobre **um** lado, não sobre o par. Há teste de id distinto.
>
> **D-4a-10 — o recorte de stage não repete `bench.unresolved`, e não carrega a
> medida do job.** Duas medidas do plano não sobreviveram ao recorte:
> `total_spill_bytes` vem de `spark.job.spill_summary`, cujo subject é o **job** —
> no recorte de um stage ela não está ausente, ela não existe, e rateá-la entre os
> stages inventaria atribuição que o event log não dá. Sai por construção
> (`_STAGE_MEASURES`), não por falta de dado. E o furo de medida por símbolo
> **não** emite `bench.unresolved`: o furo é da comparação e já foi nomeado uma
> vez no recorte do run; repeti-lo por símbolo daria ruído proporcional ao número
> de stages e afogaria o resto da saída. A chave simplesmente falta no delta — que
> é como este motor diz "não sei". As regras de presença por chave (`usable` /
> `partial` / `absent`) valem no recorte de stage pelo **mesmo** código:
> `_side_totals` passou a receber a spec e `_compare` é um caminho só para os dois
> recortes.
>
> **Símbolo repetido no mesmo lado** (o caso que o plano não previa): o recorte é
> o **símbolo**, não o stage. O mesmo `symbol` nasce várias vezes num run — linha
> dentro de laço, função chamada duas vezes — e as medidas somam todos os stages
> dele. Casar par a par exigiria ordem ou `stage_id`, que é justamente o que D-3
> proíbe. Para que a soma não minta, o próprio `bench.stage_delta` carrega
> `before_stage_count` e `after_stage_count`: sem eles, dois stages antes contra um
> depois sairia como "acelerou 50%" quando um stage apenas sumiu. Há teste.

```python
def test_stage_com_symbol_identico_casa_e_o_resto_e_contado():
    before = [_analyzed("a.jsonl"), _stage("scan", 0, mean_ms=200), _stage("join_antigo", 1)]
    after = [_analyzed("b.jsonl"), _stage("scan", 7, mean_ms=100), _stage("join_novo", 8)]

    facts = build_benchmark(before, after)

    matched = [f for f in facts if f.kind == "bench.stage_delta"]
    assert [f.subject["symbol"] for f in matched] == ["scan"]
    assert matched[0].measures["total_task_ms_delta_pct"] == -50.0

    unmatched = sorted(f.attrs["symbol"] for f in facts if f.kind == "bench.unmatched")
    assert unmatched == ["join_antigo", "join_novo"]

    sentinela = [f for f in facts if f.kind == "bench.analyzed"][0]
    assert sentinela.measures["matched_stage_count"] == 1
    assert sentinela.measures["unmatched_stage_count"] == 2


def test_stage_id_diferente_nao_impede_o_casamento():
    """`stage_id` NAO e estavel entre execucoes -- o mesmo stage sai com id
    diferente em cada run. Casar por id produziria pares errados; o teste acima
    ja usa ids 0 e 7 para o mesmo `scan`, e este fixa a intencao."""
    before = [_analyzed("a.jsonl"), _stage("scan", 0)]
    after = [_analyzed("b.jsonl"), _stage("scan", 99)]
    assert len([f for f in build_benchmark(before, after) if f.kind == "bench.stage_delta"]) == 1
```

- [x] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_facts_benchmark.py -k stage -v`
Expected: FAIL — nenhum `bench.stage_delta`
Medido: 13 falhas, 24 passando. Todas pelo motivo previsto (`assert [] == ['scan']`, `assert 0 == 3`) — nenhuma por erro de construção do teste.

- [x] **Step 3: Implemente**

Agrupe os facts de stage por `subject["symbol"]` em cada lado. `symbol` presente nos dois → `bench.stage_delta`, com subject `{"type": "stage", "symbol": <symbol>}` — **sem `stage_id`**, porque ele difere entre os runs e entraria no `Fact.id` fazendo a identidade do delta depender de um número instável. `symbol` num lado só → `bench.unmatched`, com `attrs.side` em `{"before", "after"}`.

Símbolo vazio ou ausente **não casa com nada**: vira `bench.unmatched` com `attrs.reason: "empty_symbol"`. Casar dois vazios juntaria stages que só têm em comum o fato de não terem nome. **Um fact por stage sem nome**, e não um por lado: agrupá-los repetiria dentro do lado o erro que o casamento recusa entre os lados.

O `reason` do outro caso é `"symbol_absent_on_other_side"`, com `attrs.side`, `attrs.symbol`, `attrs.stage_ids` e `measures.stage_count` — o grupo pode cobrir mais de um stage.

- [x] **Step 4: Rode**

Run: `python -m pytest tests/test_facts_benchmark.py -q`
Expected: PASS
Medido: 37 passando (24 da Task 1 + 13 novos). `ruff check .` limpo.

- [x] **Step 5: Commit**

- [x] **Step 6 (revisão da Task 2): seis desvios medidos pelo revisor**

> **D-4a-11 — o `#side` no subject fechava a colisão pela metade, e a correção
> óbvia reprova no schema.** O `stage_id` só entrava no subject quando era `int`
> não negativo; fora disso o subject de **todos** os stages sem nome daquele lado
> virava `{"type":"stage","symbol":"#before"}`. Medido pelo revisor: 647 colisões
> em 4000 com `stage_id` livre, zero quando restrito a inteiro — e
> `_facts_from_dicts` (`_core.py:1049`) copia o subject verbatim, então o arquivo
> de facts alcança o ramo defeituoso. **A correção sugerida —
> `subject["stage_id"] = str(stage_id)` sempre — não passa:** `fact.schema.json`
> exige `stage_id` inteiro ≥ 0, e `validate_fact` rejeita `'a' is not of type
> 'integer'` (medido). A identidade do stage sem nome foi então inteira para o
> `symbol` do subject — `{"type":"stage","symbol":"#<side>#<stage_id>"}` —, que
> aceita qualquer valor, com `attrs["stage_ids"]` guardando o legível. O teste
> novo usa `stage_id` **não numérico** e valida contra o schema, então o ramo é
> exercitado nos dois eixos.
>
> **D-4a-12 — símbolo casado que perde a medida num lado fabrica melhora, e agora
> tem nome.** `_side_totals` afere presença dentro dos facts que **existem**,
> nunca por stage que deveria ter contribuído: com `gc(x)=10, gc(y)=10` antes e
> `gc(x)=5` depois — `y` casado pelos facts de duração — o lado depois sai
> `usable` e o run afirma −75% que ninguém observou. É o "piso contra total" que o
> docstring promete impedir, e a justificativa anterior ("o furo já foi nomeado no
> recorte do run") era **falsa** para essa forma. Sai `bench.unresolved` com
> `reason: "measure_absent_for_matched_symbol"`, símbolo e medida. Detectável
> **só** a partir desta task, que é a primeira vez que o módulo sabe quais
> símbolos existem nos dois lados.
>
> **D-4a-13 — e o `_delta_pct` daquela medida sai do `bench.run_delta`. Medido
> antes de decidir: ruído ZERO.** As duas fixtures de `fixtures/eventlog/` nas
> quatro combinações produzem **0** furos e **0** `bench.unresolved` de qualquer
> tipo; nenhum `_delta_pct` do run cai. Não é sorte: `event_log.py` co-emite os
> kinds de stage para todo stage analisado — inclusive `spark.stage.spill` com
> zero byte, conforme o comentário em `event_log.py:516` —, então dois lados
> vindos do extrator têm sempre os mesmos kinds por símbolo. Com o número na mão a
> decisão é **omitir**: custo zero na entrada bem formada, e o percentual só
> desaparece onde ele seria inventado — a mesma escolha que a Task 1 fez para
> chave parcial e para base zero, pelo mesmo motivo. Os totais **ficam**, porque
> foram observados; o que não se sustenta é a razão entre eles.
>
> **Assimetria deliberada, com teste:** símbolo **não casado** não tira
> percentual nenhum. Stage que sumiu entre os runs é mudança de *trabalho* — a
> verdade que o benchmark existe para relatar —, enquanto símbolo casado sem a
> medida num lado é mudança de *medição*. `bench.unmatched` já nomeia o primeiro.
>
> **D-4a-14 — spill por stage existe, e o D-4a-10 dizia que não.**
> `spark.stage.spill` traz `memory_spill_bytes`/`disk_spill_bytes` por stage
> (`event_log.py:236`), e o próprio `spark.job.spill_summary` é a soma dele
> (`event_log.py:528-544`). O que é job-scoped é **o resumo**, não o spill. O
> recorte de stage passou a ler o kind certo, com o **mesmo nome de chave**
> (`total_spill_bytes`) nos dois recortes, para `SF-BENCH-003` não precisar saber
> de qual fact veio. O teste antigo virou o que ele realmente provava: o resumo do
> job **não vaza** para o recorte de stage.
>
> **D-4a-15 — `_delta_pct` do stage sai quando a população de stages muda.** Dois
> `scan` antes contra um depois, custo idêntico em cada um, dava −50% — queda por
> stage que ninguém observou. Em todo outro caso onde a comparação não se sustenta
> este módulo omite o percentual; população diferente não é exceção. Os totais e
> as duas contagens ficam, e `attrs["delta_pct_omitted"] = "stage_count_changed"`
> diz por que a chave sumiu — chave ausente é "não sei", mas "não sei" sem motivo
> escrito vira suspeita de bug.
>
> **D-4a-16 — `stage_delta_count` na sentinela.** `matched_stage_count = 3` com
> **um** `bench.stage_delta` está correto e se lê errado. O nome já diz `stage`, e
> o que faltava era o outro número ao lado. Contar os `bench.stage_delta` da saída
> não substitui: o verbo `benchmark` pagina (`_facts_page`), e uma página não é o
> total.

---

## Task 3: superfície e registro

**Files:**
- Modify: `tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `tests/test_adapters_tools.py`, `tests/test_adapters_cli.py`, `parity.yaml`, `manifest.json`, `scripts/regen_fixtures.py`

> **Tres desvios medidos contra o texto desta task.**
>
> **D-4a-17 — o helper que le facts de arquivo chama-se `_load_facts_file`, nao
> `_facts_from_file`.** `analyze_call_graph` (`_core.py:968`) e `fuse_facts` usam
> o nome real; `_facts_from_file` nao existe no repositorio. O plano ja mandava
> conferir, e a conferencia deu outro nome.
>
> **D-4a-18 — o laco de corpus de `FIXTURES_BENCH` ganhou guarda de
> existencia, e e o unico que tem.** `fixtures/bench/` nasce na Task 4, e o laco
> completo de `scripts/regen_fixtures.py` roda no intervalo entre as duas:
> `iterdir()` num diretorio ausente levanta `FileNotFoundError` e derrubaria a
> regeneracao de TODOS os dezessete corpus anteriores, que ja rodaram acima. A
> guarda fica depois da Task 4 tambem: o mesmo intervalo se repete no proximo
> dominio novo, e o custo dela e uma chamada de `is_dir()`.
>
> **D-4a-19 — o vermelho esperado sao DOIS testes, nao um.** Alem de
> `test_every_kind_of_every_extractor_appears_in_some_golden[benchmark]`, cai
> `test_every_unresolved_kind_is_exercised` — recorte explicito sobre a
> maquinaria de ponto cego, e `bench.unresolved` e um dos cinco kinds sem golden.
> Mesma causa, mesma correcao na Task 4. `test_no_tool_is_orphan` tambem acende,
> como o enunciado previa: `sparkforge_benchmark` so e citado por coordenador na
> Task 7.
>
> **O outputSchema do tool reusa `_ANALYZE_PYSPARK_SCHEMA` por identidade**
> (`_BENCHMARK_SCHEMA`), e nao o de `analyze_call_graph`: `benchmark_runs` passa
> `"bench.unresolved"` a `_facts_page`, entao a saida TEM `unresolved` e
> `unresolved_at`. `analyze_call_graph` nao tem ponto cego proprio; este modulo
> tem, e o schema precisa dizer isso.

- [x] **Step 1: As duas listas `EXTRACTORS`**

`benchmark` no import e na coleção dos **dois** arquivos — tupla em `test_rules_catalog_reachability.py`, dict em `test_fixtures_kind_coverage.py`. Esquecer uma é o modo de falha desta task, e já aconteceu com `emr_cluster` na 5b.

Run: `python -m pytest tests/test_fixtures_kind_coverage.py -q`
Expected: FAIL em `test_every_kind_of_every_extractor_appears_in_some_golden[benchmark]` — os cinco kinds ainda não têm golden. **É o resultado correto**; a Task 4 o fecha.

- [x] **Step 2: `_core.benchmark_runs`**

Na forma de `analyze_call_graph` (`_core.py:967`), mas com **dois** arquivos de facts:

```python
def benchmark_runs(
    before_path: str,
    after_path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    before = _facts_from_file(before_path)
    after = _facts_from_file(after_path)
    facts = build_benchmark(before, after, path_hint=f"{before_path}..{after_path}")
    return _facts_page(facts, "bench.unresolved", kind, limit, cursor)
```

Confira o nome real do helper que `analyze_call_graph` usa para ler facts de arquivo antes de copiar `_facts_from_file` — se for outro, use o de lá.

- [x] **Step 3: CLI**

Subcomando de topo `benchmark` (não sob `analyze`: ele não extrai de artefato, compara dois conjuntos já extraídos — mesma razão de `fuse` ser verbo próprio). `--before` e `--after` obrigatórios, mais `--out`, `--kind`, `--limit`, `--cursor`. Handler `_cmd_benchmark`, entrada `("benchmark", None)` no dict de dispatch.

- [x] **Step 4: MCP**

`sparkforge_benchmark` em `TOOLS`, com `inputSchema` de `before_path`/`after_path`/`kind`/`limit`/`cursor`. A `description` diz o que o fact carrega **e o que ele recusa**: `total_task_ms` é tempo de task somado, não tempo de relógio, e o comparador não executa nada.

Depois: as **três** listas manuais de `tests/test_adapters_tools.py` que a Fase 5c descobriu — o `set(TOOLS) == {...}` literal, o branch de `_real_output_for` e `FAILABLE`. Sem a segunda, o teste falha com `AssertionError: sem construtor de argumentos reais`.

- [x] **Step 5: `parity.yaml` e `manifest.json`**

```yaml
  - name: compare two Spark runs from their event log facts
    tools: [sparkforge_benchmark]
    cli: [benchmark]
    knowledge: [knowledge/spark/execution-model.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      codex: [cli, files]
      copilot_ci: [cli, files]
```

E `"sparkforge_benchmark"` na lista de tools do `manifest.json`, em ordem alfabética.

- [x] **Step 6: `regen_bench` em `scripts/regen_fixtures.py`**

```python
def regen_bench(directory: Path) -> None:
    """Fixture de benchmark tem DOIS event logs: `before.jsonl` e `after.jsonl`
    sob input/, extraidos com `extract_event_log_path` e comparados por
    `build_benchmark`. O golden guarda so os derivados -- repetir os de entrada
    faria uma mudanca em `event_log.py` quebrar dois goldens pelo mesmo motivo."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    before = extract_event_log_path(input_dir / "before.jsonl", repo_root=input_dir)
    after = extract_event_log_path(input_dir / "after.jsonl", repo_root=input_dir)
    facts = build_benchmark(before, after, path_hint=directory.name)
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)
```

Mais o import, `FIXTURES_BENCH` e o par na lista de matches. **E o laço de corpus completo** — a Fase 5c mediu que esquecê-lo faz o golden nascer vazio.

- [x] **Step 7: Rode e commite**

Run: `python -m pytest tests/test_adapters_cli.py tests/test_adapters_tools.py tests/test_capability_parity.py -q`
Expected: PASS

---

## Task 4: fixtures e golden

**Files:**
- Create: `fixtures/bench/*` (seis), `tests/test_fixtures_golden_bench.py`

> **Dois desvios medidos contra o texto desta task.**
>
> **D-4a-20 — `one_side_missing` nao tem `input/after.jsonl`, e a ausencia e o
> artefato.** O enunciado pede dois event logs por fixture; esta e a unica que
> tem um. A medicao que forcou o desvio: `extract_event_log` emite
> `spark.log_analyzed` INCONDICIONALMENTE, no fim da funcao
> (`event_log.py:600`), para todo arquivo que ele consegue abrir -- vazio, so
> com linha em branco, so com JSON que nao e evento, tudo produz a sentinela
> mais um punhado de `spark.unresolved`. Nao existe CONTEUDO de event log que
> deixe um lado sem ela. O unico caminho real e a falha de abertura
> (`extract_event_log_path`, ramo `except OSError`, `event_log.py:644`), que e
> exatamente o que um `--after` apontando para log que nunca foi coletado
> produz. As alternativas eram editar `event_log.py` (proibido: mudar o extrator
> para a fixture caber inverte a direcao da prova) ou escrever os facts a mao
> (o golden deixaria de ser derivado de artefato). O `str(exc)` do
> `FileNotFoundError` carrega o path ABSOLUTO da maquina, mas ele nao vaza para
> o golden: `regen_bench` guarda so a saida de `build_benchmark`, e o
> `spark.unresolved` de entrada fica de fora -- o corpus continua reproduzivel
> em qualquer maquina. O `proves` do meta.yaml daquela fixture registra tudo
> isso no lugar onde quem for mexer nela vai olhar primeiro.
>
> **D-4a-21 — `TestGolden` tem SEIS testes, nao quatro.** O Step 2 pede quatro e
> manda seguir a estrutura de `test_fixtures_golden_callgraph.py`, que tem sete.
> Os quatro nomeados (facts, findings, kinds declarados, regras declaradas) sao
> os de igualdade contra o golden; ficaram tambem
> `test_everything_validates_against_schema` e
> `test_derivation_is_deterministic`, que todos os outros modulos golden do repo
> tem. Sem eles este dominio seria o unico cujo golden nao prova que os facts
> passam no `fact.schema.json` -- e `bench.unmatched` de stage sem nome usa
> `symbol` sintetico (`"#after#9"`) justamente para caber no schema, entao a
> validacao aqui verifica uma decisao real do modulo, nao formalidade.
>
> **A guarda `is_dir()` de `FIXTURES_BENCH` FICA** (o Step 4 do enunciado mandava
> decidir e dizer por que). `fixtures/bench/` agora existe, entao ela nao e mais
> necessaria -- mas o D-4a-18 ja tinha respondido antes de o diretorio nascer, e
> a medicao nao mudou: o custo e uma chamada de `is_dir()` por execucao, e o
> intervalo que ela protege (corpus declarado no script antes de existir no
> disco) se repete inteiro no proximo dominio novo. Tirar a guarda agora seria
> desfazer a protecao no exato momento em que ela deixou de doer, para
> reintroduzi-la na proxima fase.

- [x] **Step 1: Os seis diretórios**

Cada um com `input/before.jsonl`, `input/after.jsonl` e `meta.yaml`. Os event logs são JSONL no formato que `event_log.py` já lê — copie a forma de `fixtures/eventlog/*/input/` em vez de inventar, e confira rodando `analyze event-log` antes de aceitar.

| Fixture | Prova |
|---|---|
| `regression_slower` | positivo de `SF-BENCH-002` |
| `different_input_volume` | positivo de `SF-BENCH-001` — e as outras **continuam avaliando** (D-4) |
| `faster_but_spilling` | positivo de `SF-BENCH-003` |
| `most_stages_renamed` | positivo de `SF-BENCH-004` |
| `clean_improvement` | negativo das quatro |
| `one_side_missing` | `bench.unresolved` |

Os `expects_kinds` do conjunto precisam cobrir os cinco kinds, senão o vermelho da Task 3 não fecha.

**Nesta task todo `findings.json` sai vazio e todo `expects_rules` é `[]`** — as regras nascem na Task 5, que regenera.

- [x] **Step 2: `tests/test_fixtures_golden_bench.py`**

Estrutura de `tests/test_fixtures_golden_callgraph.py`: `REQUIRED_FIXTURES` com os seis nomes, `run_fixture` extraindo os dois lados e chamando `build_benchmark`, e a classe `TestGolden` com os quatro testes.

- [x] **Step 3: Gere e leia o diff**

Run: `python scripts/regen_fixtures.py` e depois `git diff --stat fixtures/`
Nenhuma fixture fora de `fixtures/bench/` pode mudar.

- [x] **Step 4: Rode e commite**

Run: `python -m pytest tests/test_fixtures_golden_bench.py tests/test_fixtures_kind_coverage.py -q`
Expected: PASS, incluindo o `[benchmark]` que a Task 3 deixou vermelho

---

## Task 5: as quatro regras

**Files:**
- Create: `rules/catalog/benchmark.yaml`
- Modify: `fixtures/bench/*/meta.yaml`, `manifest.json`, `README.md`

- [x] **Step 1: Cabeçalho do catálogo**

Registra: por que `runtime_scope: {}` (gatilho é comparação de medida); por que a comparação vive no comparador e não no `when`; **por que `total_task_ms` não é tempo de relógio**; e por que `SF-BENCH-001` não suprime as outras (D-4 do spec).

- [x] **Step 2: `SF-BENCH-001` — volumes divergentes**

```yaml
  - id: SF-BENCH-001
    category: benchmark
    title: Comparação entre execuções com volumes de entrada diferentes
    requires_facts: [bench.run_delta]
    when:
      same_subject: true
      all:
        - fact: bench.run_delta
          expr: "abs(measures.total_input_bytes_delta_pct) > threshold.input_divergence_pct"
    status: structural
    severity_default: P0
    runtime_scope: {}
    thresholds: {input_divergence_pct: 10}
    explanation: >
      As duas execuções não leram a mesma quantidade de dado, então a diferença de tempo,
      de spill e de memória entre elas não é atribuível à mudança de código — é atribuível
      ao volume. É a forma mais comum de benchmark mentiroso, e ela não se corrige lendo o
      resultado com cuidado: se corrige refazendo a medição sobre o mesmo recorte.
      Esta regra NÃO cala as outras. Elas afirmam sobre o que foi medido; este achado diz
      que o que foi medido não sustenta conclusão sobre a mudança. Ler as duas coisas
      juntas é o que dá o quadro certo, e suprimir uma delas daria um quadro falso.
    proposed_change:
      - "Refazer as duas execuções sobre o mesmo recorte de dado: mesma partição, mesmo intervalo, mesmo filtro."
      - "Se o volume não puder ser fixado, comparar medidas normalizadas por byte lido em vez de totais — e dizer isso no relatório."
    risks:
      - "Fixar o recorte pode esconder o efeito da mudança sobre volume variável, que às vezes é o efeito procurado."
    tradeoffs:
      - "Recorte fixo mede a mudança com precisão e não mede como ela se comporta com o dado crescendo."
    validation:
      - "Comparar `total_input_bytes_before` e `total_input_bytes_after` do fact citado: a diferença precisa cair abaixo do limiar depois de refazer."
    rollback: ["Nenhum — este achado é sobre a medição, não sobre o código."]
    sources:
      - {origin: field-heuristic, note: "10% é decisão de campo. Não há fonte oficial que diga a partir de quanto uma divergência de volume invalida a comparação; o número está aqui para ser ajustado com evidência, não para ser citado como autoridade."}
```

Confira a forma real de `thresholds` e de `expr` em `rules/catalog/spark-ui.yaml` antes de copiar — se o motor não expuser `threshold.` no contexto de `expr`, use o valor literal e registre o desvio.

- [x] **Step 3: `SF-BENCH-002`, `003` e `004`**

- **002** — `expr: "measures.total_task_ms_delta_pct > threshold.regression_pct"`, P1. A `explanation` diz que `total_task_ms` é tempo de task somado e que um job pode terminar antes no relógio somando mais tempo de task ao paralelizar melhor — então o achado pede confirmação no relógio antes de reverter.
- **003** — `where` sobre delta de tempo negativo **e** delta de spill ou de GC positivo, P1. Ganho frágil.
- **004** — sobre `bench.analyzed`, `expr` com `unmatched_stage_count / (matched + unmatched)` acima do limiar, P2.

As três seguem o bloco completo de `SF-BENCH-001` acima e precisam dos mesmos campos, sem exceção: `requires_facts`, `when` com `same_subject: true`, `status`, `severity_default`, `runtime_scope: {}`, `thresholds`, `explanation`, `proposed_change`, `risks`, `tradeoffs`, `validation`, `rollback` e `sources` com `origin: field-heuristic` nomeando o número como decisão de campo. Regra sem `risks` ou sem `validation` é reprovada pelo esquema do catálogo — confira em `rules/catalog/README.md` antes de escrever, não depois de falhar.

- [x] **Step 4: Regenere, leia o diff, confira o D-4**

Run: `python scripts/regen_fixtures.py && git diff fixtures/bench/`

Confira: `different_input_volume` acende `SF-BENCH-001` **e** o que mais for verdade sobre ele — se acender só a 001, a supressão que o D-4 proíbe entrou por acidente. `clean_improvement` continua vazia.

- [x] **Step 5: Contagem de regras**

`test_docs_coverage.py::test_rule_count_equals_the_real_catalog` exige `manifest.json.rule_count == len(load_catalog())`: 62 → 66. O `README.md` cita o número duas vezes.

**Medido nesta task.** `python scripts/regen_fixtures.py` sobre o corpus inteiro mudou **quatro** arquivos, e só eles — os `findings.json` de `different_input_volume` (0 -> 2: `SF-BENCH-001` **e** `SF-BENCH-002`), `regression_slower` (0 -> 1: `SF-BENCH-002`), `faster_but_spilling` (0 -> 1: `SF-BENCH-003`) e `most_stages_renamed` (0 -> 1: `SF-BENCH-004`). `clean_improvement` e `one_side_missing` continuam com `findings.json` vazio, e `git diff --stat` não toca uma fixture fora de `fixtures/bench/`. Catálogo: **62 -> 66 regras, 11 -> 12 áreas**. Suíte inteira: **3270 passed / 2 failed / 5 skipped**; `ruff check .` limpo. Os dois vermelhos fecham na Task 7: `test_no_tool_is_orphan` (herdado) e `test_no_area_is_orphan`, que é exatamente o vermelho que o Step 1 da Task 7 manda provocar — a área `SF-BENCH` existe e ainda não tem coordenador que a declare em `rule_areas`.

**Seis desvios medidos nesta task.**

> **D-4a-22 — o campo é `threshold`, singular, e o YAML do plano escrevia `thresholds`.** Medido em `rules/engine.py` (`rule.get("threshold")`, em `_severity_for`, em `_build_finding` e no `judge`) e nas 16 ocorrências do catálogo real (`spark-ui.yaml`, `iceberg.yaml`, `parquet.yaml`, `athena.yaml`, `pyspark.yaml`, `emr-infra.yaml`). Com `thresholds:` o motor não levanta erro nenhum: ele monta o contexto de `expr` com `threshold: {}`, o avaliador levanta "caminho ausente no contexto", `_expr_matches` engole o `ExprError` e a regra **nunca dispara, em silêncio** — o falso negativo mudo que o `_validate_conditions` do carregador existe para perseguir em outra forma. As quatro regras usam `threshold:`. `expr` **expõe** `threshold.` no contexto (`engine._fact_context`, `expr.ALLOWED_ROOTS`), então nenhum limiar virou literal.

> **D-4a-23 — `abs()` não existe no avaliador, e a `SF-BENCH-001` do plano dependia dele.** `rules/expr.py` tem whitelist de nós AST e `ast.Call` **não** está nela — é fronteira de segurança declarada, porque o catálogo é dado editável. O `expr: "abs(measures.total_input_bytes_delta_pct) > threshold..."` do plano teria sido reprovado por `load_catalog(validate_exprs=True)` com "no nao permitido: Call". O módulo é feito à mão, com as duas comparações: `> threshold.input_divergence_pct or < -threshold.input_divergence_pct`. `ast.UnaryOp`/`USub` sobre `threshold.` é permitido, então o limiar continua sendo **um** número editável, e não dois que alguém pode dessincronizar. Divergência para menos conta tanto quanto para mais: ler metade do dado depois fabrica melhora com a mesma facilidade com que ler o dobro fabrica regressão.

> **D-4a-24 — `status` é `confirmed`, e o plano escreveu `structural`.** O critério do `rules/catalog/README.md` é explícito: "`status: structural` para análise estática. Só use `confirmed` quando há `measures` de execução real." Toda medida destas quatro regras vem de dois event logs de execução real, atravessando `event_log.py` e `benchmark.py` sem passar por AST nenhum. `structural` aqui teria posto a área inteira do lado errado da única distinção que o campo faz, e num domínio onde ela é o argumento central — o benchmark existe justamente porque medir não é ler código.

> **D-4a-25 — `SF-BENCH-003` compara os TOTAIS, não os `_delta_pct`, e as duas razões foram medidas.** O plano pedia "`where` sobre delta de tempo negativo e delta de spill ou de GC positivo". Medido: (1) `benchmark.py::_delta_pct` OMITE a chave quando o lado antes é zero, e é exatamente o caso de **spill que nasce** — antes 0, depois 160 MB, a forma mais severa de "mais rápido mas derramando" — que ficaria invisível; nas fixtures, `total_spill_bytes_delta_pct` não existe em `clean_improvement` nem em `most_stages_renamed`, porque o spill é zero dos dois lados. (2) `expr.py` avalia `BoolOp` de forma **eager** (`values = [_eval(v, ctx, depth + 1) for v in node.values]`, sem curto-circuito), então um `spill or gc` com a chave de spill ausente levanta `ExprError` e derruba a condição inteira, **inclusive o ramo de GC que estava presente e verdadeiro**. O gatilho final compara `after > before * threshold.growth_factor` para spill e para GC: os totais existem sempre que a medida é utilizável nos dois lados, e com base zero a comparação degenera para "qualquer byte derramado", que é o comportamento desejado. O que permanece — se uma das duas medidas for inutilizável em algum lado a condição inteira cai — está escrito na `explanation` e no cabeçalho do arquivo, com o `bench.unresolved` como o lugar onde o operador vê o silêncio.

> **D-4a-26 — `same_subject: true` nas quatro, com uma condição só, e o motivo é o D-5c-31.** Sem ele, `engine._evaluate_when` produz no máximo **um** grupo de evidência, logo um Finding, mesmo com vários pares comparados no mesmo conjunto de facts. O subject de `bench.run_delta` e de `bench.analyzed` é `{type: job_run, symbol: <path_hint>}`, então o grupo é o PAR comparado — exatamente a entidade sobre a qual cada regra afirma. Sem efeito no golden de hoje (cada fixture compara um par só), e é por isso que a decisão precisa estar escrita: nenhuma fixture a defenderia se ela fosse revertida. A escolha de âncora da `SF-BENCH-004` segue o mesmo raciocínio pelo lado oposto: ela fala de **proporção**, que é afirmação sobre o conjunto, e por isso lê a sentinela `bench.analyzed` e não cada `bench.unmatched` — ancorá-la no órfão produziria um achado por stage renomeado, ruído com o volume da própria mudança.

> **D-4a-27 — a área nova acende um segundo vermelho, e ele é o do Step 1 da Task 7.** `62 -> 66` em `manifest.json` e nas três menções do `README.md` (o Step 5 dizia duas; são três — a terceira está na seção "Camada determinística"), mais a distribuição por área da linha 35, que passou a 12 áreas com `SF-BENCH` 4. Junto, `rules/catalog/README.md` ganhou `BENCH` na lista de siglas do campo `id` e `benchmark.yaml` na tabela "Arquivos". `knowledge/sources.lock.json` **não** muda: as quatro regras citam só `origin: field-heuristic`, e o lock vigia `sources` com `url`. O que passou a falhar é `test_agent_coverage.py::test_no_area_is_orphan`, e isso não é regressão: é o vermelho que a Task 7 existe para fechar, provocado no momento em que a área nasceu.

---

## Task 6: `benchmark_ref` citando `fact_id`

**Files:**
- Modify: `sparkforge/findings/validate.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `tests/test_findings_validate.py`

- [x] **Step 1: A camada de forma, que sempre vale**

```python
_BENCH_REF = re.compile(r"^f_[0-9a-f]{6}$")


def _reject_unbacked_gain(payload: dict[str, Any], fact_ids: set[str] | None = None) -> None:
    effect = payload.get("expected_effect") or ""
    if not effect or not _QUANTIFIED.search(effect):
        return
    ref = payload.get("benchmark_ref")
    if not ref:
        raise ValidationFailed(
            f"expected_effect quantifica ganho ({effect!r}) sem benchmark_ref. "
            "Ganho previsto sem benchmark e invencao."
        )
    if not _BENCH_REF.match(str(ref)):
        raise ValidationFailed(
            f"benchmark_ref {ref!r} nao e um fact_id. Desde a Fase 4a o campo cita o "
            "`fact_id` de um `bench.run_delta` -- texto livre nao prova medicao nenhuma."
        )
    if fact_ids is not None and str(ref) not in fact_ids:
        raise ValidationFailed(
            f"benchmark_ref {ref!r} nao esta no conjunto de facts informado. "
            "O achado cita uma medicao que nao acompanha a evidencia."
        )
```

Teste primeiro, com os quatro casos: sem `benchmark_ref` (rejeita, comportamento antigo), com texto livre (rejeita, **novo**), com `fact_id` de forma válida e sem conjunto de facts (aceita), com `fact_id` ausente do conjunto informado (rejeita).

- [x] **Step 2: `validate_finding` ganha o parâmetro opcional**

```python
def validate_finding(payload: dict[str, Any], fact_ids: set[str] | None = None) -> None:
    _check(payload, "finding.schema.json")
    _reject_unbacked_gain(payload, fact_ids)
```

Parâmetro **opcional** porque `validate_finding` é chamado de dentro do golden e do motor, onde o conjunto de facts nem sempre está à mão. A camada de forma vale sempre; a de pertinência, quando alguém puder provar.

- [x] **Step 3: O verbo `validate` aceita `--facts`**

`_core.validate_output(finding, facts_path=None)` lê o arquivo quando informado e passa o conjunto de `fact_id`. A tool MCP espelha com `facts_path` opcional.

- [x] **Step 4: A quebra de contrato, declarada**

Rode a suíte inteira. **Se algum teste ou fixture existente tiver `benchmark_ref` em texto livre, ele passa a falhar — e isso é o objetivo, não um acidente.** Corrija cada caso citando um `fact_id` real, e liste no relatório quantos eram. Se forem muitos, pare e reporte antes de mexer: pode indicar que a quebra precisa de flag em vez de valer de imediato.

- [x] **Step 5: Commit**

**Medido nesta task.** Suíte inteira: **3290 passed / 2 failed / 5 skipped** (+20 testes; eram 3270 passed). `ruff check .` limpo. Os dois vermelhos são os mesmos da Task 5 — `test_no_tool_is_orphan` e `test_no_area_is_orphan` — e fecham na Task 7.

**Cinco desvios medidos nesta task.**

> **D-4a-28 — a quebra de contrato atinge UM caso, não muitos, e o número foi medido antes de mexer.** O Step 4 mandava parar e reportar se fossem muitos. Contagem real de `benchmark_ref` fora de `build/` (artefato de build, ignorado): **83 ocorrências em 63 arquivos de `fixtures/`, todas `""`**; **zero** no catálogo (`rules/**/*.yaml` — `engine.py:204` lê `rule.get("benchmark_ref", "")` e nenhuma regra declara o campo); nos testes, **um** único valor em texto livre, `tests/test_findings_validate.py::test_quantified_effect_with_benchmark_is_accepted` com `"bench/2026-07-29-coalesce.json"`. Esse teste virou `TestBenchmarkRefCitesAFactId::test_free_text_benchmark_ref_is_rejected` — o mesmo valor, agora provando a rejeição em vez da aceitação, que é a forma honesta de registrar uma inversão de contrato. Um caso não justifica flag: a quebra vale de imediato.

> **D-4a-29 — a forma só é cobrada onde o gate morde, e isso é fronteira, não esquecimento.** `_reject_unbacked_gain` retorna cedo quando `expected_effect` não quantifica, então um achado com efeito qualitativo e `benchmark_ref` em prosa **continua passando**. É consequência direta de onde o plano pôs a checagem (dentro da função de ganho), e está certo: o gate existe para ganho sem lastro, não para higiene de campo. O que não pode é a fronteira ficar implícita — `test_a_qualitative_effect_does_not_care_about_the_shape` a fixa por teste, para que mudá-la seja decisão e não deriva.

> **D-4a-30 — `finding.schema.json` ganhou `description`, e deliberadamente NÃO ganhou `pattern`.** O schema dizia só `{"type": "string"}` sobre `benchmark_ref`. Um `"pattern": "^(f_[0-9a-f]{6})?$"` seria tentador e estaria errado por dois motivos medidos: (1) o schema é incondicional, então ele rejeitaria prosa também em achado sem ganho quantificado — quebra maior do que a fase pediu; (2) `_check` roda **antes** de `_reject_unbacked_gain`, então o erro de schema (`benchmark_ref: '...' does not match ...`) chegaria primeiro e a mensagem que explica *por que* o campo mudou ficaria inalcançável justamente para quem bate nela. A `description` documenta a forma e o motivo de ela não estar no schema. Contraste: `evidence` **tem** `pattern: ^f_[0-9a-f]{6}$` no schema desde a Fase 0 — lá a exigência é incondicional, aqui não.

> **D-4a-31 — `fact_ids is not None`, e não `if fact_ids`.** Conjunto vazio é falsy; com o teste por veracidade, `validate_finding(payload, set())` desligaria a camada de pertinência **em silêncio** e todo `fact_id` bem formado passaria — o oposto exato do que "informei o conjunto e ele está vazio" significa. Mesma classe do `thresholds` do D-4a-22: nada levanta erro, a regra só para de valer. `test_an_empty_fact_set_is_not_the_same_as_no_fact_set` fixa a distinção.

> **D-4a-32 — o padrão vive em `validate.py` sem importar `models.py`, e um teste liga os dois.** `validate` opera sobre payload (dict cru vindo de JSON), nunca sobre `Fact`; importar o modelo só para reaproveitar uma regex acoplaria as duas camadas na direção errada. O preço é duas fontes para a mesma forma, e ele é pago por `test_the_expected_shape_is_the_shape_fact_id_really_has`, que constrói um `Fact` real e casa o `id` dele contra `_BENCH_REF` — se `Fact.id` mudar de forma (outro digest, outro truncamento), o teste cai em vez de o gate passar a rejeitar todo mundo.

---

## Task 7: coordenador, skill e fechamento

**Files:**
- Modify: `agents/spark-performance-architect.md`, `skills/benchmark-pyspark-job/SKILL.md`, `docs/superpowers/STATUS.md`, `README.md`, `AGENTS.md`

- [ ] **Step 1: Prove a órfã primeiro**

Run: `python -m pytest tests/test_agent_coverage.py -v`
Expected: FAIL em `test_no_area_is_orphan` — `SF-BENCH` sem coordenador. Cole a saída.

- [ ] **Step 2: `SF-BENCH` em `rule_areas`**

Em `agents/spark-performance-architect.md`. Sem coordenador novo (D-6 do spec): a pergunta — *o job ficou mais rápido, e por quê* — é a que esse coordenador já responde.

- [ ] **Step 3: A skill ganha o fluxo**

`skills/benchmark-pyspark-job/SKILL.md`: coletar event log antes, aplicar a mudança, coletar depois, `sparkforge benchmark --before ... --after ...`, `judge`, e citar o `fact_id` do `bench.run_delta` no `benchmark_ref` do achado. Toda invocação de `judge` passa runtime — invariante de `tests/test_skill_content.py`.

Depois: `python scripts/sync_skills.py`.

- [ ] **Step 4: Meça os números**

```bash
python -c "
from sparkforge.rules.loader import load_catalog
import collections
r = load_catalog(); print('regras', len(r))
print(dict(sorted(collections.Counter(x['id'].rsplit('-',1)[0] for x in r).items(), key=lambda kv:-kv[1])))
"
python -c "
import importlib, pkgutil; import sparkforge.facts as F
k=set(); n=0
for m in pkgutil.iter_modules(F.__path__):
    mod = importlib.import_module('sparkforge.facts.'+m.name)
    if hasattr(mod,'EMITTED_KINDS'): n+=1; k |= set(mod.EMITTED_KINDS)
print('extratores', n, 'kinds', len(k))
from sparkforge.adapters.tools import TOOLS; print('tools', len(TOOLS))
"
ls -d fixtures/*/*/ | wc -l ; ls -d fixtures/*/ | wc -l
python -m pytest -q 2>&1 | tail -2
```

- [ ] **Step 5: `STATUS.md`, `README.md`, `AGENTS.md`**

Tabela de números com os valores **medidos**. Seção "Fase 4a" no formato das anteriores: o defeito de partida (gate sem produtor), o que entrou, **a quebra de contrato do `benchmark_ref`**, e a faixa de commits. Na §16 do roadmap, marcar que a Fase 4 está **parcialmente** fechada — 4b tem validação funcional, gates fail-closed e assinatura.

`README.md` e `AGENTS.md` na mesma passada: contagens, e o verbo `benchmark` na tabela de extratores/verbos. A varredura de docs desta sessão mediu que documento de topo não tem invariante que o defenda — então ele entra no fechamento da fase, não depois.

- [ ] **Step 6: Suíte, ruff, commit**
