---
sdd: 1
feature: DATABRICKS_PHOTON_PLAN
phase: plan
profile: dev
status: draft
upstream:
  path: docs/sdd/DATABRICKS_PHOTON_PLAN/design.md
  sha256: "35e8417d733c178e3eb907a6e2234aed089aef5fcfceab3ba47000b04294634b"
tasks:
  - id: T1
    files: [tests/test_databricks_photon_plan.py, sparkforge/facts/spark_plan.py, fixtures/plan/photon_join, fixtures/plan/photon_udf, tests/test_fixtures_golden_plan.py, docs/claims.lock.json]
    covers: [AC1, AC3]
    test: {path: tests/test_databricks_photon_plan.py, name: test_plano_photon_gera_fact_de_photon}
  - id: T2
    files: [tests/test_databricks_photon_plan.py, sparkforge/rules/engine.py]
    covers: [AC2, AC7]
    test: {path: tests/test_databricks_photon_plan.py, name: test_fact_de_photon_recusa_regra_de_plano_sem_declaracao}
  - id: T3
    files: [tests/test_databricks_photon_plan.py, sparkforge/adapters/_core.py, sparkforge/facts/runtime_detect.py]
    covers: [AC4, AC5]
    test: {path: tests/test_databricks_photon_plan.py, name: test_photon_off_contra_plano_photon_diverge}
  - id: T4
    files: [tests/test_databricks_photon_plan.py, sparkforge/facts/spark_plan.py, rules/catalog/spark-plan.yaml, fixtures/plan/python_udf_in_plan, fixtures/plan/photon_udf]
    covers: [AC6]
    test: {path: tests/test_databricks_photon_plan.py, name: test_arrow_eval_python_nao_afirma_pandas}
  - id: T5
    files: [tests/test_databricks_photon_plan.py, knowledge/databricks/runtime-matrix.md, knowledge/offline-manifest.json, docs/surface.lock.json]
    covers: [AC8]
    test: {path: tests/test_databricks_photon_plan.py, name: test_knowledge_registra_o_extrator_sob_photon}
---

# DATABRICKS_PHOTON_PLAN — plano

Regras de toda tarefa: as de
`C:\Users\edgar\AppData\Local\Temp\claude\E--projetos-spark-forge-aws\aecdc55f-7550-4610-801b-0b1e6d24fd0a\scratchpad\contexto.md`
(edição por ferramenta, LF, commit por `git commit -F`, gate de lastro antes do commit
com `.py` novo ou bytes movidos, NUNCA rodar `tests/test_agents_parity.py`), mais:
a máquina tem pouca memória — rode só os testes nomeados, um comando por vez, nunca
os lotes; branch `sdd/databricks-photon-plan`.

## T1 — `plan.photon`

1. Fixtures. `fixtures/plan/photon_join/input/plan.txt` recebe EXATAMENTE este texto
   (observado em Databricks Free Edition, serverless, Spark 4.2.0, 2026-09-18, sobre
   `spark.range`):

```text
== Physical Plan ==
AdaptiveSparkPlan (17)
+- == Initial Plan ==
   PhotonResultStage (16)
   +- PhotonColumnarToRow (15)
      +- PhotonProject (14)
         +- PhotonBroadcastHashJoin Inner (13)
            :- PhotonGroupingAgg (7)
            :  +- PhotonShuffleExchangeSource (6)
            :     +- PhotonShuffleMapStage (5)
            :        +- PhotonShuffleExchangeSink (4)
            :           +- PhotonGroupingAgg (3)
            :              +- PhotonProject (2)
            :                 +- PhotonRange (1)
            +- PhotonShuffleExchangeSource (12)
               +- PhotonShuffleMapStage (11)
                  +- PhotonShuffleExchangeSink (10)
                     +- PhotonProject (9)
                        +- PhotonRange (8)


(1) PhotonRange
Output [1]: [id#11254L]
Arguments: Range (0, 2000000, step=1, splits=8)

(2) PhotonProject
Input [1]: [id#11254L]
Arguments: [id#11254L, (id#11254L % 100) AS k#11256L]

(3) PhotonGroupingAgg
Input [2]: [id#11254L, k#11256L]
Arguments: [k#11256L], [partial_count(1) AS count#11266L, partial_sum(id#11254L) AS sum#11268L], [count#11265L, sum#11267L], [k#11256L, count#11266L, sum#11268L], false

(4) PhotonShuffleExchangeSink
Input [3]: [k#11256L, count#11266L, sum#11268L]
Arguments: hashpartitioning(k#11256L, 16)

(5) PhotonShuffleMapStage
Input [3]: [k#11256L, count#11266L, sum#11268L]
Arguments: ENSURE_REQUIREMENTS, [id=#7384]

(6) PhotonShuffleExchangeSource
Input [3]: [k#11256L, count#11266L, sum#11268L]
Arguments: false

(7) PhotonGroupingAgg
Input [3]: [k#11256L, count#11266L, sum#11268L]
Arguments: [k#11256L], [finalmerge_count(merge count#11266L) AS count(1)#11263L, finalmerge_sum(merge sum#11268L) AS sum(id)#11264L], [count(1)#11263L, sum(id)#11264L], [k#11256L, count(1)#11263L AS n#11257L, sum(id)#11264L AS s#11258L], true

(8) PhotonRange
Output [1]: [id#11259L]
Arguments: Range (0, 100, step=1, splits=8)

(9) PhotonProject
Input [1]: [id#11259L]
Arguments: [id#11259L AS k#11260L, concat(c, cast(id#11259L as string)) AS nome#11262]

(10) PhotonShuffleExchangeSink
Input [2]: [k#11260L, nome#11262]
Arguments: SinglePartition

(11) PhotonShuffleMapStage
Input [2]: [k#11260L, nome#11262]
Arguments: EXECUTOR_BROADCAST, [id=#7394]

(12) PhotonShuffleExchangeSource
Input [2]: [k#11260L, nome#11262]
Arguments: false

(13) PhotonBroadcastHashJoin
Left keys [1]: [k#11256L]
Right keys [1]: [k#11260L]
Join type: Inner
Join condition: None

(14) PhotonProject
Input [5]: [k#11256L, n#11257L, s#11258L, k#11260L, nome#11262]
Arguments: [k#11256L, n#11257L, s#11258L, nome#11262]

(15) PhotonColumnarToRow
Input [4]: [k#11256L, n#11257L, s#11258L, nome#11262]

(16) PhotonResultStage
Input [4]: [k#11256L, n#11257L, s#11258L, nome#11262]

(17) AdaptiveSparkPlan
Output [4]: [k#11256L, n#11257L, s#11258L, nome#11262]
Arguments: isFinalPlan=false


== Photon Explanation ==
The query is fully supported by Photon.
```

   `fixtures/plan/photon_udf/input/plan.txt`:

```text
== Physical Plan ==
PhotonResultStage (8)
+- PhotonColumnarToRow (7)
   +- PhotonProject (6)
      +- PhotonArrowBatchSource (5)
         +- ArrowEvalPython (4)
            +- PhotonArrowResultStage (3)
               +- PhotonArrowBatchSink (2)
                  +- PhotonRange (1)


(1) PhotonRange
Output [1]: [id#11274L]
Arguments: Range (0, 2000000, step=1, splits=8)

(2) PhotonArrowBatchSink
Input [1]: [id#11274L]
Arguments: -1, 4096, 5242880, 33554432, false, false, -1, false, 0, true, HashSet()

(3) PhotonArrowResultStage
Input [1]: [id#11274L]

(4) ArrowEvalPython
Input [1]: [id#11274L]
Arguments: [dobro(id#11274L)#11279L], [pythonUDF0#11281L], 101

(5) PhotonArrowBatchSource
Input [2]: [id#11274L, pythonUDF0#11281L]

(6) PhotonProject
Input [2]: [id#11274L, pythonUDF0#11281L]
Arguments: [pythonUDF0#11281L AS d#11280L]

(7) PhotonColumnarToRow
Input [1]: [d#11280L]

(8) PhotonResultStage
Input [1]: [d#11280L]


== Photon Explanation ==
The query is fully supported by Photon.
```

   `meta.yaml` de cada uma, no formato de `fixtures/plan/python_udf_in_plan/meta.yaml`:
   `name`, `proves` (dizendo a origem: observado em Databricks Free Edition,
   serverless, Spark 4.2.0, 2026-09-18, dados sintéticos `spark.range`), `runtime:
   {databricks: "19", spark: "4.2.0"}`, `expects_kinds` e `expects_rules` conforme o
   golden gerado (`photon_join` dispara SF-PLAN-004, pelo `isFinalPlan=false`; `photon_udf` dispara SF-PLAN-002).
   Em `tests/test_fixtures_golden_plan.py`, `REQUIRED_FIXTURES` ganha `"photon_join"`
   e `"photon_udf"`.

2. Teste, em `tests/test_databricks_photon_plan.py` (arquivo novo):

```python
"""Photon reconhecido no plano, e a recusa movida pelo artefato."""
from pathlib import Path

import yaml

from sparkforge.facts.spark_plan import extract_plan_path
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
PLANOS = ROOT / "fixtures" / "plan"


def _facts(caso: str):
    entrada = PLANOS / caso / "input"
    return extract_plan_path(entrada / "plan.txt", repo_root=entrada)


def test_plano_photon_gera_fact_de_photon():
    photon = [f for f in _facts("photon_join") if f.kind == "plan.photon"]
    assert len(photon) == 1
    fact = photon[0]
    assert fact.measures["photon_operators"] == 16
    assert fact.measures["operators"] == 17
    assert "PhotonBroadcastHashJoin" in fact.attrs["operators"]
    assert fact.attrs["operators"] == sorted(set(fact.attrs["operators"]))
    assert fact.attrs["explanation"] == "The query is fully supported by Photon."
    udf = [f for f in _facts("photon_udf") if f.kind == "plan.photon"]
    assert udf[0].measures["photon_operators"] == 7


def test_plano_sem_photon_nao_muda_veredito():
    for caso in sorted(p.name for p in PLANOS.iterdir() if p.is_dir()):
        if caso.startswith("photon_"):
            continue
        facts = _facts(caso)
        assert not any(f.kind == "plan.photon" for f in facts), caso
        meta = yaml.safe_load((PLANOS / caso / "meta.yaml").read_text(encoding="utf-8"))
        obtido = sorted(
            (f.rule_id, f.severity, repr(sorted(f.subject.items())))
            for f in judge(facts, load_catalog(), meta["runtime"])
        )
        esperado = sorted(
            (f["rule_id"], f["severity"], repr(sorted(f["subject"].items())))
            for f in __import__("json").loads(
                (PLANOS / caso / "expected" / "findings.json").read_text(encoding="utf-8")
            )
        )
        assert obtido == esperado, caso
```

   (`test_plano_sem_photon_nao_muda_veredito` passa antes e depois: é a trava de AC3;
   o vermelho da tarefa é o do primeiro teste.)

3. Vermelho: `python -m pytest tests/test_databricks_photon_plan.py::test_plano_photon_gera_fact_de_photon -q`
   — `assert 0 == 1` (nenhum `plan.photon`).

4. Código, em `sparkforge/facts/spark_plan.py`:
   - `EMITTED_KINDS` ganha `"plan.photon"`.
   - Constante `_PHOTON_PREFIX = "Photon"` e `_PHOTON_EXPLANATION = "photon explanation"`,
     com comentário citando `knowledge/databricks/runtime-matrix.md` §4 e dizendo que a
     forma vale para o observado (U1, U2 do define).
   - Método `_Parser.photon_fact(self)`: conta os nós de `self.nodes` cujo
     `operator.startswith(_PHOTON_PREFIX)`; se zero, não emite nada. Senão emite
     `Fact(kind="plan.photon", subject=_subject(self.path, <primeiro nó Photon>),
     measures={"photon_operators": n, "operators": len(self.nodes)},
     attrs={"operators": sorted({nomes Photon}), "explanation": <texto>},
     provenance=self.provenance)`. O `<texto>` é a primeira linha não vazia depois do
     marcador `== Photon Explanation ==` em `self.lines` (casado por `_SECTION_RE`,
     comparando `group(1).strip().lower()` com `_PHOTON_EXPLANATION`), ou `""`.
   - Em `extract_plan`, chamar `parser.photon_fact()` dentro do `try`, depois de
     `parser.join_side_stats()`.
5. Goldens: `mkdir -p fixtures/plan/photon_join/expected fixtures/plan/photon_udf/expected`
   e `python scripts/regen_fixtures.py photon_join photon_udf`. Conferir que nenhum
   golden de plano antigo mudou (`git status fixtures/plan`).
6. Verde: o comando do passo 3, depois
   `python -m pytest tests/test_databricks_photon_plan.py tests/test_fixtures_golden_plan.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -q`.
7. `python scripts/check_vnext_claims.py` (arquivo `.py` novo; remedie por id).
8. Commit: `feat(plan): recognize Photon operators and emit plan.photon`.

## T2 — a recusa pelo fact

1. Teste, em `tests/test_databricks_photon_plan.py`:

```python
def test_fact_de_photon_recusa_regra_de_plano_sem_declaracao():
    from sparkforge.findings.models import Fact

    base = _facts("photon_join")
    join = Fact(
        kind="plan.join",
        subject={"type": "plan_node", "file": "plan.txt", "line": 1, "symbol": "(1) X",
                 "node_id": 1, "operator": "CartesianProduct", "relation": ""},
        attrs={"strategy": "CartesianProduct"},
        provenance={"extractor": "teste"},
    )
    achados, pulados = judge([*base, join], load_catalog(), {"spark": "4.2.0"}, return_skipped=True)
    assert "SF-PLAN-003" not in {f.rule_id for f in achados}
    assert {"rule_id": "SF-PLAN-003", "reason": "databricks.photon.unresolved"} in pulados
    sem_photon = judge([join], load_catalog(), {"spark": "4.2.0"})
    assert "SF-PLAN-003" in {f.rule_id for f in sem_photon}


def test_udf_sob_photon_continua_julgada():
    achados = judge(_facts("photon_udf"), load_catalog(), {"spark": "4.2.0"})
    assert "SF-PLAN-002" in {f.rule_id for f in achados}
    aqe = judge(_facts("photon_join"), load_catalog(), {"spark": "4.2.0"})
    assert "SF-PLAN-004" in {f.rule_id for f in aqe}
```

2. Vermelho: `python -m pytest tests/test_databricks_photon_plan.py::test_fact_de_photon_recusa_regra_de_plano_sem_declaracao -q`
   — `AssertionError` em `"SF-PLAN-003" not in ...`.
3. Código, em `sparkforge/rules/engine.py`: `_photon_recusa(rule, runtime, present_kinds)`
   passa a disparar quando `"plan.photon" in present_kinds` OU (runtime databricks e
   photon `on`). `_PHOTON_NAO_CALA` ganha `"plan.aqe"`, com o motivo: o nó
   `AdaptiveSparkPlan` continua no plano Photon observado (§4), e SF-PLAN-004 lê esse
   nó, não um operador Photon. A chamada em `judge` passa
   `present_kinds`. Atualize o comentário acima de `_PLAN_KIND_PREFIXES` e o docstring
   do módulo com a segunda via (o artefato).
4. Verde: o mesmo comando, `test_udf_sob_photon_continua_julgada`, e
   `python -m pytest tests/test_rules_engine.py tests/test_databricks_platform.py tests/test_fixtures_golden_plan.py -q`.
5. Commit: `feat(rules): refuse plan rules when the plan itself shows Photon`.

## T3 — a detecção lê o plano

1. Teste:

```python
def test_photon_off_contra_plano_photon_diverge():
    from sparkforge.adapters._core import build_runtime

    context, facts = build_runtime(databricks="19", photon="off", facts=_facts("photon_join"))
    assert context.photon == "on"
    assert any(d.startswith("photon:") for d in context.divergences)
    estado = next(f for f in facts if f.kind == "databricks.photon")
    assert (estado.attrs["state"], estado.attrs["source"]) == ("on", "plan")


def test_plano_photon_cala_sf_env_006():
    from sparkforge.adapters._core import build_runtime

    context, facts = build_runtime(databricks="19", facts=_facts("photon_join"))
    assert "SF-ENV-006" not in {f.rule_id for f in judge(facts, load_catalog(), context.to_dict())}
    _, sem_plano = build_runtime(databricks="19")
    assert "SF-ENV-006" in {f.rule_id for f in judge(sem_plano, load_catalog(), {"databricks": "19"})}
```

2. Vermelho: `python -m pytest tests/test_databricks_photon_plan.py::test_photon_off_contra_plano_photon_diverge -q`
   — `assert 'off' == 'on'`.
3. Código:
   - `sparkforge/adapters/_core.py::_runtime_reading`: `if fact.kind == "plan.photon": return ("plan", "photon", "on")`,
     com comentário (observação do artefato, não declaração).
   - `sparkforge/facts/runtime_detect.py`: `_photon` separa observação (toda fonte que
     não é `cli`) de declaração (`cli`). Observação válida vence; declaração que
     discorda dela gera a divergência `photon: o plano mostra Photon (fonte plan) e a
     declaracao cli diz off; vale o artefato`. `_photon_fact(photon, fonte)` grava
     `source` = `"plan"` quando veio de observação, `"cli"` quando de declaração,
     `"none"` sem nada. A divergência "declarado sem plataforma databricks" continua
     só para declaração `cli`; observação sem plataforma databricks não entra no
     contexto nem gera divergência (a recusa pelo engine já vale pelo fact, T2).
     Retorne de `_photon` o que o `detect_runtime` precisa para as três coisas (valor,
     fonte, divergência), sem duplicar a leitura das fontes.
4. Verde: os dois testes; `python -m pytest tests/test_databricks_platform.py tests/test_fixtures_golden_runtime.py tests/test_capability_parity.py tests/test_runtime_detect.py -q`.
   `tests/test_capability_parity.py` exige produtor para eixo de `RuntimeContext`:
   `photon` continua em `AXES_DECLARED_ONLY`? Agora ele TEM produtor (`plan.photon` em
   `_runtime_reading`). Se o teste
   `test_declared_only_axes_are_real_axes_without_producer` falhar, tire `photon` de
   `AXES_DECLARED_ONLY` e ajuste o parágrafo do docstring dizendo por quê (produtor
   desde esta feature). Isso entra neste commit.
5. `python scripts/check_vnext_claims.py`.
6. Commit: `feat(runtime): a Photon plan is an observation that outranks the declaration`.

## T4 — `ArrowEvalPython` não afirma pandas

1. Teste:

```python
def test_arrow_eval_python_nao_afirma_pandas():
    udf = [f for f in _facts("photon_udf") if f.kind == "plan.python_udf"]
    assert [f.attrs["udf_type"] for f in udf] == ["arrow"]
    regra = next(r for r in load_catalog() if r["id"] == "SF-PLAN-002")
    achado = next(
        f for f in judge(_facts("photon_udf"), [regra], {"spark": "4.2.0"})
    )
    texto = " ".join(str(x) for x in (achado.explanation, *achado.proposed_change))
    assert "é `pandas_udf`" not in texto
    assert "pandas_udf já é a escolha certa" not in texto
```

2. Vermelho: `python -m pytest tests/test_databricks_photon_plan.py::test_arrow_eval_python_nao_afirma_pandas -q`
   — `assert ['pandas'] == ['arrow']`.
3. Código:
   - `sparkforge/facts/spark_plan.py`, `_PYTHON_UDF_OPERATORS`: `"ArrowEvalPython": "arrow"`,
     com comentário: o nó é o mesmo para `pandas_udf` e para UDF Python otimizada para
     Arrow, e o plano não diz qual (observado em §4).
   - `rules/catalog/spark-plan.yaml`, SF-PLAN-002: `when` vira
     `any: [{fact: plan.python_udf, where: {attrs.udf_type: pandas}}, {fact: plan.python_udf, where: {attrs.udf_type: arrow}}]`
     mantendo `same_subject: true`; título "UDF vetorizada ou serializada em Arrow no
     plano — nativo ainda é mais rápido"; `explanation` troca a primeira frase por
     "`ArrowEvalPython` é UDF com transferência colunar por Arrow em vez de pickle linha
     a linha — `pandas_udf` ou UDF Python otimizada para Arrow; o plano não diz qual."
     (o resto do parágrafo fica); `proposed_change` 2 vira "Se não for, manter — a UDF
     já usa Arrow, que é a forma certa quando uma UDF é necessária."; `tradeoffs` troca
     "Trocar pandas_udf" por "Trocar a UDF"; o comentário de escopo cita
     `ArrowEvalPython` e os operadores pandas.
   - Ajuste o `proves` de `fixtures/plan/python_udf_in_plan/meta.yaml` (hoje diz
     "`ArrowEvalPython` (pandas UDF, vetorizada)").
4. Goldens: `python scripts/regen_fixtures.py python_udf_in_plan photon_udf`; o diff
   de `python_udf_in_plan` é só `udf_type` e o texto de SF-PLAN-002; o veredito igual
   (confirme com `test_plano_sem_photon_nao_muda_veredito`).
5. Verde: o comando do passo 2, e o bloco de regra de `docs/gates-por-mudanca.md`:
   `python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py -q`,
   e `python -m pytest tests/test_rule_scope_by_nature.py tests/test_fixtures_golden_plan.py tests/test_databricks_rule_audit.py -q`.
6. `python scripts/check_vnext_claims.py`.
7. Commit: `fix(plan): ArrowEvalPython is an Arrow UDF, not necessarily pandas`.

## T5 — o documento

1. Teste:

```python
def test_knowledge_registra_o_extrator_sob_photon():
    texto = (ROOT / "knowledge" / "databricks" / "runtime-matrix.md").read_text(encoding="utf-8")
    secao = texto.split("## 4.", 1)[1]
    assert "plan.photon" in secao
    assert "databricks.photon.unresolved" in secao
    assert "udf_type" in secao and "arrow" in secao
```

2. Vermelho: `python -m pytest tests/test_databricks_photon_plan.py::test_knowledge_registra_o_extrator_sob_photon -q`
   — `assert 'plan.photon' in ...`.
3. Texto, em `knowledge/databricks/runtime-matrix.md` §4: o parágrafo que registra o
   extrator calado e o `udf_type` enganoso vira o que o SparkForge faz desde esta
   feature: reconhece os operadores `Photon*` e emite `plan.photon`; com ele, as regras
   de plano saem em `skipped` com `databricks.photon.unresolved` sem precisar de
   `--photon`, exceto as de UDF; uma declaração que discorda vira divergência; e o
   `ArrowEvalPython` sai com `udf_type: arrow`. Mantenha o registro histórico de que o
   extrator era calado (uma frase, com a data), e acrescente os limites (forma
   observada num ambiente; texto de suporte parcial não visto). NÃO mexa na tabela da
   seção 1.
4. Registros: sha256 no `knowledge/offline-manifest.json` por
   `sparkforge.tools.offline._content_sha256`; `python scripts/check_surface_lock.py --update`;
   `python scripts/verify_offline_bundle.py`;
   `python -m pytest tests/test_offline_expansion.py tests/test_surface_lock.py tests/test_runtime_matrix_drift.py -q`.
5. Verde: o comando do passo 2; `python scripts/check_vnext_claims.py`.
6. Commit: `docs(knowledge): what SparkForge does with a Photon plan now`.
