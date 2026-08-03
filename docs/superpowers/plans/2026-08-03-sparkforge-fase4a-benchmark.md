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
> **D-4a-1 — `DERIVER_ID` virou `EXTRACTOR_ID`.** Os onze módulos de
> `sparkforge/facts/`, inclusive os dois derivados (`call_graph.py`, `fusion.py`),
> declaram `EXTRACTOR_ID`, e `tests/test_facts_fusion.py` e
> `tests/test_facts_catalog_schema.py` asseguram o prefixo por esse nome. Um nome
> só para este módulo seria diferença sem diferença.
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
> **D-4a-4 — `before_artifact` virou `before_artifacts`, lista ordenada.** Não há
> exatamente um `spark.log_analyzed` por lado: event log rolante
> (`spark.eventLog.rolling.enabled`) e extração de vários arquivos produzem
> vários. Pegar o primeiro esconderia os outros.
>
> **D-4a-5 — totais passam por `_round`.** `mean_ms` é média (`sum/n`), então
> `mean_ms * task_count` carrega ruído de ponto flutuante que entraria no
> `Fact.id` e faria o golden depender de bit de arredondamento. Arredonda só o que
> é `float`; byte e contagem de task continuam inteiros.

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

- [ ] **Step 1: Teste primeiro**

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

- [ ] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_facts_benchmark.py -k stage -v`
Expected: FAIL — nenhum `bench.stage_delta`

- [ ] **Step 3: Implemente**

Agrupe os facts de stage por `subject["symbol"]` em cada lado. `symbol` presente nos dois → `bench.stage_delta`, com subject `{"type": "stage", "symbol": <symbol>}` — **sem `stage_id`**, porque ele difere entre os runs e entraria no `Fact.id` fazendo a identidade do delta depender de um número instável. `symbol` num lado só → `bench.unmatched`, com `attrs.side` em `{"before", "after"}`.

Símbolo vazio ou ausente **não casa com nada**: vira `bench.unmatched` com `attrs.reason: "empty_symbol"`. Casar dois vazios juntaria stages que só têm em comum o fato de não terem nome.

- [ ] **Step 4: Rode**

Run: `python -m pytest tests/test_facts_benchmark.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

---

## Task 3: superfície e registro

**Files:**
- Modify: `tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `tests/test_adapters_tools.py`, `tests/test_adapters_cli.py`, `parity.yaml`, `manifest.json`, `scripts/regen_fixtures.py`

- [ ] **Step 1: As duas listas `EXTRACTORS`**

`benchmark` no import e na coleção dos **dois** arquivos — tupla em `test_rules_catalog_reachability.py`, dict em `test_fixtures_kind_coverage.py`. Esquecer uma é o modo de falha desta task, e já aconteceu com `emr_cluster` na 5b.

Run: `python -m pytest tests/test_fixtures_kind_coverage.py -q`
Expected: FAIL em `test_every_kind_of_every_extractor_appears_in_some_golden[benchmark]` — os cinco kinds ainda não têm golden. **É o resultado correto**; a Task 4 o fecha.

- [ ] **Step 2: `_core.benchmark_runs`**

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

- [ ] **Step 3: CLI**

Subcomando de topo `benchmark` (não sob `analyze`: ele não extrai de artefato, compara dois conjuntos já extraídos — mesma razão de `fuse` ser verbo próprio). `--before` e `--after` obrigatórios, mais `--out`, `--kind`, `--limit`, `--cursor`. Handler `_cmd_benchmark`, entrada `("benchmark", None)` no dict de dispatch.

- [ ] **Step 4: MCP**

`sparkforge_benchmark` em `TOOLS`, com `inputSchema` de `before_path`/`after_path`/`kind`/`limit`/`cursor`. A `description` diz o que o fact carrega **e o que ele recusa**: `total_task_ms` é tempo de task somado, não tempo de relógio, e o comparador não executa nada.

Depois: as **três** listas manuais de `tests/test_adapters_tools.py` que a Fase 5c descobriu — o `set(TOOLS) == {...}` literal, o branch de `_real_output_for` e `FAILABLE`. Sem a segunda, o teste falha com `AssertionError: sem construtor de argumentos reais`.

- [ ] **Step 5: `parity.yaml` e `manifest.json`**

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

- [ ] **Step 6: `regen_bench` em `scripts/regen_fixtures.py`**

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

- [ ] **Step 7: Rode e commite**

Run: `python -m pytest tests/test_adapters_cli.py tests/test_adapters_tools.py tests/test_capability_parity.py -q`
Expected: PASS

---

## Task 4: fixtures e golden

**Files:**
- Create: `fixtures/bench/*` (seis), `tests/test_fixtures_golden_bench.py`

- [ ] **Step 1: Os seis diretórios**

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

- [ ] **Step 2: `tests/test_fixtures_golden_bench.py`**

Estrutura de `tests/test_fixtures_golden_callgraph.py`: `REQUIRED_FIXTURES` com os seis nomes, `run_fixture` extraindo os dois lados e chamando `build_benchmark`, e a classe `TestGolden` com os quatro testes.

- [ ] **Step 3: Gere e leia o diff**

Run: `python scripts/regen_fixtures.py` e depois `git diff --stat fixtures/`
Nenhuma fixture fora de `fixtures/bench/` pode mudar.

- [ ] **Step 4: Rode e commite**

Run: `python -m pytest tests/test_fixtures_golden_bench.py tests/test_fixtures_kind_coverage.py -q`
Expected: PASS, incluindo o `[benchmark]` que a Task 3 deixou vermelho

---

## Task 5: as quatro regras

**Files:**
- Create: `rules/catalog/benchmark.yaml`
- Modify: `fixtures/bench/*/meta.yaml`, `manifest.json`, `README.md`

- [ ] **Step 1: Cabeçalho do catálogo**

Registra: por que `runtime_scope: {}` (gatilho é comparação de medida); por que a comparação vive no comparador e não no `when`; **por que `total_task_ms` não é tempo de relógio**; e por que `SF-BENCH-001` não suprime as outras (D-4 do spec).

- [ ] **Step 2: `SF-BENCH-001` — volumes divergentes**

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

- [ ] **Step 3: `SF-BENCH-002`, `003` e `004`**

- **002** — `expr: "measures.total_task_ms_delta_pct > threshold.regression_pct"`, P1. A `explanation` diz que `total_task_ms` é tempo de task somado e que um job pode terminar antes no relógio somando mais tempo de task ao paralelizar melhor — então o achado pede confirmação no relógio antes de reverter.
- **003** — `where` sobre delta de tempo negativo **e** delta de spill ou de GC positivo, P1. Ganho frágil.
- **004** — sobre `bench.analyzed`, `expr` com `unmatched_stage_count / (matched + unmatched)` acima do limiar, P2.

As três seguem o bloco completo de `SF-BENCH-001` acima e precisam dos mesmos campos, sem exceção: `requires_facts`, `when` com `same_subject: true`, `status`, `severity_default`, `runtime_scope: {}`, `thresholds`, `explanation`, `proposed_change`, `risks`, `tradeoffs`, `validation`, `rollback` e `sources` com `origin: field-heuristic` nomeando o número como decisão de campo. Regra sem `risks` ou sem `validation` é reprovada pelo esquema do catálogo — confira em `rules/catalog/README.md` antes de escrever, não depois de falhar.

- [ ] **Step 4: Regenere, leia o diff, confira o D-4**

Run: `python scripts/regen_fixtures.py && git diff fixtures/bench/`

Confira: `different_input_volume` acende `SF-BENCH-001` **e** o que mais for verdade sobre ele — se acender só a 001, a supressão que o D-4 proíbe entrou por acidente. `clean_improvement` continua vazia.

- [ ] **Step 5: Contagem de regras**

`test_docs_coverage.py::test_rule_count_equals_the_real_catalog` exige `manifest.json.rule_count == len(load_catalog())`: 62 → 66. O `README.md` cita o número duas vezes.

---

## Task 6: `benchmark_ref` citando `fact_id`

**Files:**
- Modify: `sparkforge/findings/validate.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `tests/test_findings_validate.py`

- [ ] **Step 1: A camada de forma, que sempre vale**

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

- [ ] **Step 2: `validate_finding` ganha o parâmetro opcional**

```python
def validate_finding(payload: dict[str, Any], fact_ids: set[str] | None = None) -> None:
    _check(payload, "finding.schema.json")
    _reject_unbacked_gain(payload, fact_ids)
```

Parâmetro **opcional** porque `validate_finding` é chamado de dentro do golden e do motor, onde o conjunto de facts nem sempre está à mão. A camada de forma vale sempre; a de pertinência, quando alguém puder provar.

- [ ] **Step 3: O verbo `validate` aceita `--facts`**

`_core.validate_output(finding, facts_path=None)` lê o arquivo quando informado e passa o conjunto de `fact_id`. A tool MCP espelha com `facts_path` opcional.

- [ ] **Step 4: A quebra de contrato, declarada**

Rode a suíte inteira. **Se algum teste ou fixture existente tiver `benchmark_ref` em texto livre, ele passa a falhar — e isso é o objetivo, não um acidente.** Corrija cada caso citando um `fact_id` real, e liste no relatório quantos eram. Se forem muitos, pare e reporte antes de mexer: pode indicar que a quebra precisa de flag em vez de valer de imediato.

- [ ] **Step 5: Commit**

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
