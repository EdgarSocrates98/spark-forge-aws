# SparkForge Fase 4c — validação funcional: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** provar que a mudança preservou a semântica — contagem, schema, chaves e agregados —, com um plano que o motor deriva dos facts que já tem e um resultado que o operador produz.

**Architecture:** `funcval plan` deriva e emite `funcval.plan`, que satisfaz o gate `functional_validation_defined`. `funcval compare` é módulo derivado no padrão de `benchmark.py` — função pura sobre `Fact`s, que nunca executa.

**Tech Stack:** Python stdlib, YAML declarativo, pytest.

**Spec:** [`../specs/2026-08-04-sparkforge-fase4c-validacao-funcional-design.md`](../specs/2026-08-04-sparkforge-fase4c-validacao-funcional-design.md) — §9 tem os dez critérios, §3 o limite que define o que a fase pode prometer.

---

## Fatos do ambiente verificados antes de escrever este plano

```
pyspark.write   attrs [mode, target]                      <- alvo, deriva
pyspark.join    measures [on_arity]  attrs [how, has_broadcast_hint]
                                                          <- NUMERO de chaves, NAO os nomes
catalog_schema  catalog.table_schema, catalog.table_partitions,
                catalog.table_property, catalog.analyzed, catalog.unresolved

routing.yaml gates:
  functional_validation_defined: {advisory_reason: "sem produtor ate a Fase 4c"}

benchmark.py e o padrao do comparador: EXTRACTOR_ID, EMITTED_KINDS, funcao pura,
  presenca por CHAVE e nao por kind, _delta_pct omitido em base zero,
  _round a 3 casas, unresolved com subject proprio (Fact.id ignora attrs)

test_adapters_tools.py  QUATRO listas manuais (medido na Fase 4b)
```

**A consequência que decide a Task 1, e ela corrige o spec:** a §4 do spec afirma
que *"`pyspark.join` dá as chaves"*. **Não dá.** O fact carrega `on_arity` — o
número de colunas do `on` — e nunca os nomes. Chave de negócio não é derivável de
fact nenhum hoje.

Isso não invalida a fase: contagem, schema e partição continuam deriváveis. Mas a
Task 1 tem que decidir o que fazer com o eixo de chaves, e a decisão vai para a
seção de desvios do spec — não para uma reescrita.

---

## Task 1: o que é derivável, medido — e o que fazer com as chaves

Antes de qualquer código. É a Task 0 de pesquisa em outra forma: aqui a fonte é o
próprio repositório, e a Fase 4b provou que essa medição muda o desenho.

**Files:** nenhum. Produz medição e decisão, escritas no plano.

- [ ] **Step 1: Para cada um dos quatro eixos, responda com evidência**

Contagem, schema, chaves, agregados. Para cada um:

1. Que fact, se presente, dá o que o check precisa? Procure nos `EMITTED_KINDS`
   de **todos** os extratores — não invente kind.
2. O que exatamente ele carrega? Nome de coluna, tipo, ou só contagem?
3. Se nada der, o eixo depende de **entrada do operador** — e isso é decisão, não
   falha.

Cole a tabela.

- [ ] **Step 2: Decida o eixo de chaves, com o custo dos dois caminhos**

Três saídas, e nenhuma é obviamente certa:

- **O operador declara** (`funcval plan --key <col>[,<col>]`). Honesto: é entrada,
  não derivação. Custo: o plano deixa de ser 100% derivado, e o `funcval.plan`
  precisa distinguir check derivado de check declarado — senão a procedência mente.
- **Partição como proxy de chave.** Barato e **errado**: coluna de partição não é
  chave, e um check de unicidade sobre ela acusaria dado correto. Se você escolher
  isto, precisa de argumento muito bom.
- **Sem eixo de chaves nesta fase**, com o limite declarado e o gancho para quando
  algum extrator nomear chave.

Meça o custo e decida. Registre no plano e prepare o texto do desvio para o spec.

- [ ] **Step 3: Meça também o que o resultado do operador precisa carregar**

O comparador lê JSON que o operador produz. Que campos ele precisa para que
`SF-FVAL-001..005` sejam avaliáveis? Derive das regras da §6 do spec, não da
imaginação — e escreva o contrato mínimo.

- [ ] **Step 4: Commit da medição**

---

## Task 2: `funcval plan`

**Files:**
- Create: `sparkforge/facts/funcval.py`, `tests/test_facts_funcval.py`

- [ ] **Step 1: O teste que falha**

```python
from sparkforge.facts.funcval import EMITTED_KINDS, build_plan
from sparkforge.findings.models import Fact


def _write(target: str) -> Fact:
    return Fact(
        kind="pyspark.write",
        subject={"type": "source_location", "file": "job.py", "line": 10,
                 "col": 0, "symbol": "", "snippet": ""},
        attrs={"mode": "overwrite", "target": target},
        provenance={"artifact": "job.py", "extractor": "pyspark_ast@0.1.0"},
    )


def test_o_plano_deriva_o_alvo_do_write():
    facts = build_plan([_write("db.vendas")])
    plano = [f for f in facts if f.kind == "funcval.plan"][0]
    assert plano.attrs["target"] == "db.vendas"
    assert "count" in plano.attrs["checks"]


def test_cada_check_cita_o_fact_de_origem():
    """Plano sem procedencia seria julgamento vestido de derivacao."""
    facts = build_plan([_write("db.vendas")])
    plano = [f for f in facts if f.kind == "funcval.plan"][0]
    assert plano.attrs["derived_from"]


def test_sem_write_nao_ha_alvo_e_o_plano_nao_e_inventado():
    facts = build_plan([])
    assert [f.kind for f in facts if f.kind == "funcval.plan"] == []
    assert [f.kind for f in facts if f.kind == "funcval.unresolved"] == ["funcval.unresolved"]
```

- [ ] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_facts_funcval.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implemente**

Módulo no padrão de `benchmark.py`: `EXTRACTOR_ID`, `EMITTED_KINDS` com os
**quatro** kinds da §5 do spec (`funcval.plan`, `funcval.check_delta`,
`funcval.analyzed`, `funcval.unresolved`), asserção final de namespace,
`sort_facts` no retorno.

`build_plan(facts, path_hint="")` deriva o que a Task 1 mediu ser derivável. Cada
check carrega o `fact_id` de origem. Alvo sem write vira `funcval.unresolved`,
nunca alvo adivinhado.

- [ ] **Step 4: Rode e commite**

---

## Task 3: `funcval compare`

**Files:**
- Modify: `sparkforge/facts/funcval.py`, `tests/test_facts_funcval.py`

- [ ] **Step 1: O teste que falha**

```python
def test_contagem_divergente_vira_check_delta():
    plano = {"target": "db.vendas", "checks": ["count"]}
    antes = {"count": 1000}
    depois = {"count": 998}
    facts = build_comparison(plano, antes, depois)
    delta = [f for f in facts if f.kind == "funcval.check_delta"][0]
    assert delta.attrs["check"] == "count"
    assert delta.attrs["diverged"] is True


def test_float_dentro_da_tolerancia_nao_diverge():
    """Soma de float depende da ordem de reducao: um repartition legitimo muda o
    total nos ultimos bits. Comparacao exata daria falso positivo justamente na
    mudanca que a fase existe para aprovar."""
    plano = {"target": "t", "checks": ["sum_valor"], "types": {"sum_valor": "double"}}
    facts = build_comparison(plano, {"sum_valor": 1_000_000.0},
                             {"sum_valor": 1_000_000.000001})
    assert [f for f in facts if f.kind == "funcval.check_delta"][0].attrs["diverged"] is False


def test_inteiro_e_comparado_exato():
    plano = {"target": "t", "checks": ["count"], "types": {"count": "bigint"}}
    facts = build_comparison(plano, {"count": 1000}, {"count": 1001})
    assert [f for f in facts if f.kind == "funcval.check_delta"][0].attrs["diverged"] is True


def test_check_do_plano_ausente_no_resultado_e_contado():
    """Validacao parcial lida como aprovacao e o encontro de 'nenhum problema'
    com 'nao coletei'. SF-FVAL-005 le esta contagem."""
    plano = {"target": "t", "checks": ["count", "schema"]}
    facts = build_comparison(plano, {"count": 1}, {"count": 1})
    sentinela = [f for f in facts if f.kind == "funcval.analyzed"][0]
    assert sentinela.measures["planned_check_count"] == 2
    assert sentinela.measures["reported_check_count"] == 1
```

O formato de `plano`, `antes` e `depois` é o que a Task 1 Step 3 mediu — ajuste
os literais acima ao contrato que ela fixou.

- [ ] **Step 2: Rode, implemente, rode**

Exata para inteiro, decimal, contagem e schema. Tolerância relativa **só** para
ponto flutuante, com o limiar vindo do catálogo (não hardcoded no módulo, pelo
mesmo motivo que nenhum limiar do repositório mora em Python).

Reuse a disciplina de `benchmark.py`, que a revisão da 4a validou: presença por
**chave** e não por kind; `unresolved` com subject próprio, porque `Fact.id`
ignora `attrs` e os unresolved colidiriam; e `_round` onde float entrar em
`measures`, porque ruído de bit entraria no `Fact.id` e o golden dependeria dele.

- [ ] **Step 3: A saída declara o limite**

`funcval.analyzed` carrega, em `attrs`, a declaração de que os quatro são
**proxies** — contagem, schema, chaves e agregados iguais não provam que o dado é
o mesmo. §3 do spec, critério 8. Não é comentário no código: é campo na saída.

- [ ] **Step 4: Commite**

---

## Task 4: superfície

**Files:**
- Modify: `sparkforge/adapters/{_core,cli,tools}.py`, as duas listas `EXTRACTORS`, as **quatro** de `tests/test_adapters_tools.py`, `parity.yaml`, `manifest.json`, `scripts/regen_fixtures.py`

- [ ] **Step 1: Os dois verbos**

`funcval plan --facts <arquivo> --out <arquivo>` e
`funcval compare --plan <arquivo> --before <arquivo> --after <arquivo>`.

Subcomando de topo, como `benchmark` — não sob `analyze`, porque não extrai de
artefato.

Confira a assinatura real de `_load_facts_file` e de `_facts_page` antes de
copiar: a Fase 4a mediu que o plano chutou `_facts_from_file`, nome que não existe.

- [ ] **Step 2: As listas**

Duas `EXTRACTORS` (tupla e dict, arquivos diferentes) e as **quatro** de
`test_adapters_tools.py`: o `set(TOOLS)` literal, o branch de `_real_output_for`,
`FAILABLE` e `_WRITE_IDEMPOTENT` — esta última porque `funcval plan --out`
escreve.

- [ ] **Step 3: `parity.yaml`, `manifest.json`, `regen_funcval`**

- [ ] **Step 4: O vermelho esperado**

`test_every_kind_of_every_extractor_appears_in_some_golden[funcval]` fica
vermelho até a Task 5. **Não crie fixture para silenciá-lo.** Reporte.

---

## Task 5: fixtures e golden

**Files:**
- Create: `fixtures/funcval/*`, `tests/test_fixtures_golden_funcval.py`

- [ ] **Step 1: Os casos**

| Fixture | Prova |
|---|---|
| `count_diverged` | `SF-FVAL-001` |
| `schema_diverged` | `SF-FVAL-002` |
| `duplicate_key_appeared` | `SF-FVAL-003` |
| `aggregate_outside_tolerance` | `SF-FVAL-004` |
| `aggregate_within_tolerance` | negativo de `SF-FVAL-004` — o repartition legítimo |
| `partial_coverage` | `SF-FVAL-005` |
| `clean_equivalence` | **negativo das cinco** |

Se a Task 1 decidiu que o eixo de chaves não entra nesta fase,
`duplicate_key_appeared` sai e a razão fica escrita.

- [ ] **Step 2: Golden do domínio, no molde de `test_fixtures_golden_bench.py`**

- [ ] **Step 3: Regenere, leia o diff, rode**

Nesta task `findings.json` sai vazio — as regras nascem na Task 6.

---

## Task 6: as cinco regras, e o gate que endurece

**Files:**
- Create: `rules/catalog/funcval.yaml`
- Modify: `rules/catalog/routing.yaml`, `fixtures/funcval/*`, `manifest.json`, `README.md`

- [ ] **Step 1: O cabeçalho**

Registra: `runtime_scope: {}` (gatilho é comparação de valor); por que a
comparação vive no comparador e não no `when`; **o limite dos proxies**; e por que
a tolerância existe só para ponto flutuante.

- [ ] **Step 2: As cinco**

`SF-FVAL-001` (contagem, P0), `002` (schema, P0), `003` (chave duplicada, P0),
`004` (agregado fora da tolerância, P1), `005` (cobertura parcial, P1).

Cada uma com `same_subject: true` — a Fase 5c mediu (D-5c-31) que sem ele o motor
produz **um** grupo de evidência, e N divergências viram um achado ancorado na
primeira.

A `explanation` de cada uma diz que os quatro são proxies. A de `004` diz que
divergência dentro da tolerância **não é prova de igualdade**, é ausência de prova
de diferença.

O campo de limiar é **`threshold`, singular** — a Fase 4a mediu (D-4a-22) que o
plural não levanta erro: o motor monta contexto vazio, `_expr_matches` engole o
`ExprError`, e a regra fica inerte para sempre.

- [ ] **Step 3: O gate endurece**

`rules/catalog/routing.yaml`, `functional_validation_defined`: troque
`advisory_reason` por `satisfied_by: funcval.plan`, `produced_by` com o comando
real, e `guards_phases` — que a Task 1 da Fase 4b mediu como decisão, não como
ordem de tupla. Meça em qual fase ele morde, pelo mesmo critério de lá: o gate não
pode morder numa fase em que a rota que o destrava ainda opera.

- [ ] **Step 4: Regenere, leia o diff, confira `clean_equivalence` vazia**

- [ ] **Step 5: Contagem de regras** — `manifest.json` e as três ocorrências no `README.md`

---

## Task 7: coordenador, skill e fechamento

**Files:**
- Modify: `agents/*.md`, `skills/*/SKILL.md`, `docs/superpowers/STATUS.md`, `README.md`, `AGENTS.md`

- [ ] **Step 1: Prove a órfã**

Run: `python -m pytest tests/test_agent_coverage.py -v`
Expected: FAIL — `SF-FVAL` sem coordenador. Cole a saída.

- [ ] **Step 2: Coordenador e skill**

Decida com argumento: coordenador novo, ou `SF-FVAL` num que já existe? A Fase 4a
pendurou `SF-BENCH` no `spark-performance-architect` porque a pergunta era a
mesma; a Fase 5c deu coordenador próprio ao `SF-DQ` porque não era. Diga qual é o
caso aqui.

Se a skill nova despachar, ela precisa da fronteira de manutenção destrutiva e da
decisão em `DISPATCHABLE_SKILLS`/`NON_DISPATCHABLE_SKILLS` — a fase do Devin
tornou isso invariante.

- [ ] **Step 3: Meça e feche**

Números medidos, seção da fase no `STATUS.md`, §16 marcada **concluída** — é o
último dos quatro itens de rigor. Dívidas registradas, com a natureza certa
(dívida, fase ou limite declarado).

- [ ] **Step 4: Suíte verde, ruff limpo, `sync_skills.py --check` OK, commit**
