# SparkForge Fase 5c.2 — um passo para dentro da chamada: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** fechar a cegueira de `SF-DQ-003` para helper de validação, herdando do chamador a evidência de persistência que o parâmetro carrega — e só quando a herança é inequívoca.

**Architecture:** o extrator já indexa por escopo (`_ScopeIndex`). Esta fase acrescenta **um** passo: quando o alvo é parâmetro e a função tem **exatamente um** call site no módulo, a evidência de persistência do argumento naquele call site é herdada. Mais de um chamador não resolve — resolve para "não sei", que é a chave omitida.

**Tech Stack:** Python stdlib (`ast`), YAML declarativo, pytest.

**Dívida que fecha:** [`STATUS.md`](../STATUS.md), linha `SF-DQ-003 não avalia check cujo alvo chega por parâmetro` (desvio D-5c-11 da [Fase 5c](../specs/2026-08-03-sparkforge-fase5c-dq-design.md)).

**Base:** a Fase 5c fechou com `target_persisted` **omitido** para parâmetro, porque afirmá-lo `false` acusava a forma canônica de biblioteca Glue — validar num helper, `cache()` no chamador. A omissão era a resposta certa **com a informação que o extrator tinha**. Esta fase amplia a informação, não a política.

---

## Fatos do ambiente verificados antes de escrever este plano

```
data_quality.py   _ScopeIndex     writes / persists / actions / rebinds / params / chained
                  _scopes         corpo do modulo + cada FunctionDef/AsyncFunctionDef
                  _target_persisted -> bool | None   (None = parametro sem evidencia local)
                  _check          omite a chave quando None

fixtures/dq/helper_validates_cached_param   fixa a omissao, 0 findings
tests/test_facts_data_quality.py            135 testes
suite  3117 passed, 5 skipped   |   catalogo 62 regras
```

**A fronteira que não se atravessa:** o extrator lê **um módulo por vez** (`extract_data_quality(tree, path)`). "Um passo para dentro da chamada" significa dentro do **mesmo arquivo**. Chamador noutro módulo continua invisível, e continua sendo omissão — não invente travessia entre arquivos, que é outra fase e outro custo.

---

## Task 1: o call site único, e a herança de persistência

**Files:**
- Modify: `sparkforge/facts/data_quality.py`, `tests/test_facts_data_quality.py`

- [x] **Step 1: Escreva o teste que falha**

```python
def test_persistencia_do_chamador_e_herdada_quando_ha_um_so_call_site():
    facts = _facts(
        "def valida(vendas):\n"
        "    ruins = vendas.filter(vendas.valor < 0).count()\n"
        "    vendas.write.parquet('s3://b/p')\n"
        "\n"
        "def main(spark):\n"
        "    entregas = spark.read.parquet('s3://b/in')\n"
        "    entregas.cache()\n"
        "    valida(entregas)\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is True


def test_dois_call_sites_nao_resolvem_e_a_chave_continua_omitida():
    facts = _facts(
        "def valida(vendas):\n"
        "    ruins = vendas.filter(vendas.valor < 0).count()\n"
        "    vendas.write.parquet('s3://b/p')\n"
        "\n"
        "def main(spark):\n"
        "    a = spark.read.parquet('s3://b/a')\n"
        "    a.cache()\n"
        "    valida(a)\n"
        "    b = spark.read.parquet('s3://b/b')\n"
        "    valida(b)\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert "target_persisted" not in check.attrs
```

O segundo teste é o mais importante dos dois: um chamador persiste e o outro não, e a resposta honesta é **não sei**. Herdar do primeiro que aparecer seria inventar.

- [x] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_facts_data_quality.py -k call_site -v`
Expected: FAIL no primeiro (`KeyError: 'target_persisted'`), PASS no segundo — ele já é o comportamento atual, e é controle.

- [x] **Step 3: O índice de call sites, por módulo**

Uma travessia que colhe, por nome de função definida no módulo, a lista de chamadas a ela — cada uma com a linha e o escopo em que ocorre. Chamada por atributo (`obj.valida(...)`) **não** conta: o nome não prova que é a função deste módulo.

Herança só quando: **uma** entrada na lista, o argumento na posição do parâmetro é um `ast.Name`, e há índice do escopo chamador. Qualquer outra coisa devolve `None` e a chave segue omitida.

- [x] **Step 4: `_target_persisted` consulta o chamador**

Quando o alvo é parâmetro e não há evidência local, resolva o call site único, mapeie o parâmetro para o nome do argumento, e pergunte a persistência **no escopo do chamador**, na linha da chamada. Reuse `_rebound_between` no escopo do chamador: religação entre o `cache()` e a chamada invalida, exatamente como invalida entre o `cache()` e o check.

**Mapeamento posicional e por keyword.** `valida(entregas)` e `valida(vendas=entregas)` são o mesmo caso. `*args`/`**kwargs` no call site não resolvem.

- [x] **Step 5: Rode**

Run: `python -m pytest tests/test_facts_data_quality.py -q`
Expected: PASS, e **os 135 anteriores continuam passando** — em especial `test_alvo_parametro_nao_afirma_persistencia_que_vive_fora_do_escopo`, que agora precisa de um call site que não resolva para continuar válido. Se ele quebrar, **não o apague**: ajuste a fonte dele para o caso que ele realmente prova (parâmetro sem chamador no módulo) e diga isso no relatório.

**Desvios medidos na Task 1**

- **D-5c2-1 — o teste da Fase 5c quebrou, como o Step 5 previu.**
  `test_alvo_parametro_nao_afirma_persistencia_que_vive_fora_do_escopo` tinha
  `main` cacheando e chamando `valida` no mesmo arquivo: exatamente o caso que
  esta fase passa a resolver, e ele virou `target_persisted: true`. A fonte foi
  ajustada para o caso que o teste realmente prova — helper de biblioteca **sem
  chamador neste módulo** —, e o comentário dele agora nomeia a fronteira (um
  módulo por vez) em vez do escopo. Nenhuma asserção foi apagada;
  `action_after_check is True` continua provando a assimetria.

- **D-5c2-2 — parâmetro religado antes do check não herda.** O limite conhecido
  da 5c (`vendas = carrega(...)` na primeira linha do helper deixa a chave
  omitida) deixaria de valer de graça: sem evento local de persistência, a
  herança responderia sobre o objeto que **entrou**, e não sobre o que o check
  valida. `_target_persisted` pergunta `_rebound_between(target, 0, line)` antes
  de sair do escopo — o mesmo predicado, com `0` abaixo de qualquer `lineno`.

- **D-5c2-3 — argumento que o chamador não liga nem persiste não resolve, e o
  caso foi medido.** Com um global cacheado no corpo do módulo
  (`entregas.cache()` fora de qualquer função) e `def main(): valida(entregas)`,
  o índice de `main` não tem evento nenhum sobre `entregas` e devolvia `false` —
  herdado, isso faria `SF-DQ-003` **acusar um DataFrame cacheado um escopo
  acima**. Dentro do próprio escopo do check esse `false` é o comportamento
  aceito da 5c; propagá-lo por herança estenderia uma acusação, e herança aqui
  só estende evidência. `_persisted_in_caller` exige que o nome esteja em
  `rebinds`, `persists` ou `params` do chamador.

- **D-5c2-4 — nome de função que não identifica uma única definição sai do
  mapa.** Duas `def valida` no módulo (ou um método homônimo a uma função de
  módulo) fazem o call site deixar de dizer qual corpo recebe o argumento.
  `_function_definitions` descarta o nome inteiro, e a chave segue omitida.

- **D-5c2-5 — a religação no escopo do chamador OMITE, e não emite `false`.**
  Está no controle 3 da Task 2, mas é uma assimetria contra a regra do próprio
  escopo do check (onde religar emite `false`) e por isso fica registrada:
  atravessando a chamada não há acusação a preservar, porque antes desta fase a
  chave já era omitida — recusar a herança não perde acusação nenhuma, só deixa
  de inventar uma. `_rebound_after_persist` isola essa pergunta.

- [x] **Step 6: Commit**

---

## Task 2: os controles que impedem a herança de mentir

**Files:**
- Modify: `tests/test_facts_data_quality.py`

- [ ] **Step 1: Seis controles, cada um com a razão no nome**

Escreva os seis, rode, e **para cada um que já passar antes de qualquer mudança, diga isso** — controle que nasce verde prova que a implementação da Task 1 não foi longe demais.

1. chamador sem `cache()` → `target_persisted: false` (herança que resolve **contra** a persistência também é herança)
2. `unpersist()` no chamador antes da chamada → `false`
3. religação do argumento entre o `cache()` e a chamada → chave omitida
4. chamada por atributo (`self.valida(entregas)`) → chave omitida
5. argumento que não é `ast.Name` (`valida(spark.table('t'))`) → chave omitida
6. função chamada dentro dela mesma (recursão) → não entra em laço, e a chave sai omitida

- [ ] **Step 2: Commit**

---

## Task 3: o gate de `SF-DQ-002`, medido antes de decidir

A dívida gêmea é consequência atrás de helper (`aborta_se(ruins)`), e ela é o **espelho** desta: ali o argumento entra na função, aqui o parâmetro sai dela. A máquina da Task 1 pode servir, e pode não servir.

- [ ] **Step 1: Meça, não presuma**

Escreva a fonte abaixo e rode o extrator:

```python
def aborta_se(ruins):
    if ruins > 0:
        raise ValueError('dado ruim')

def main(spark):
    vendas = spark.read.parquet('s3://b/in')
    ruins = vendas.filter(vendas.valor < 0).count()
    aborta_se(ruins)
    vendas.write.parquet('s3://b/out')
```

Hoje: `SF-DQ-002` acusa, porque `dq.enforcement` não é emitido. Cole a saída.

- [ ] **Step 2: Decida com o custo na mão**

A herança da Task 1 responde "de onde vem este parâmetro". Aqui a pergunta é outra: "o que a função chamada **faz** com o argumento" — exige olhar o corpo do callee e decidir se ele aborta condicionalmente ao valor recebido. É travessia nova, não reuso.

**Se for reuso genuíno da máquina da Task 1**, implemente com os mesmos limites (um call site, mesmo módulo, argumento `ast.Name`).

**Se for travessia nova**, **não implemente**: registre no `STATUS.md` que a dívida de `SF-DQ-002` não se fecha com a máquina desta fase, com o motivo medido, e feche a fase com a dívida de `SF-DQ-003` fechada e a outra aberta. Meia dívida fechada com honestidade vale mais que duas fechadas com máquina que ninguém entende.

- [ ] **Step 3: Commit da decisão, qualquer que seja**

---

## Task 4: fixtures, catálogo e fechamento

**Files:**
- Create: `fixtures/dq/helper_validates_uncached_param/`
- Modify: `fixtures/dq/helper_validates_cached_param/`, `rules/catalog/data-quality.yaml`, `docs/superpowers/STATUS.md`

- [ ] **Step 1: A fixture existente muda de veredito, e é isso que prova a fase**

`fixtures/dq/helper_validates_cached_param` foi criada na 5c para fixar a **omissão**. Depois desta fase o mesmo job resolve para `target_persisted: true`, e continua com **0 findings** — mas por um motivo diferente: antes a regra não avaliava, agora ela avalia e não dispara.

Regenere, leia o diff, e **reescreva o `proves:` do `meta.yaml`** para dizer o motivo novo. Fixture cujo texto descreve um mecanismo que deixou de existir é pior que fixture ausente.

- [ ] **Step 2: A fixture nova — herança que resolve contra**

`helper_validates_uncached_param`: mesmo formato, sem `cache()` no chamador. Prova que a herança resolve para `false` e que **`SF-DQ-003` dispara** — sem ela, a fase inteira pode ter trocado uma cegueira por outra, e nenhum golden acusaria.

Acrescente as duas a `REQUIRED_FIXTURES` em `tests/test_fixtures_golden_dq.py`.

- [ ] **Step 3: A `explanation` de `SF-DQ-003` mudou de verdade**

O texto atual declara o recorte "não persistido **neste escopo**". Depois desta fase o recorte é outro: a regra enxerga o chamador quando ele é único e está no mesmo arquivo. Reescreva, e declare o novo limite — mais de um chamador, chamador noutro módulo, chamada por atributo.

- [ ] **Step 4: `STATUS.md`**

Números medidos (fixtures, testes). A dívida de `SF-DQ-003` marcada como fechada, com o mecanismo e o preço. A de `SF-DQ-002` conforme a Task 3 decidiu.

- [ ] **Step 5: Suíte inteira, ruff, commit**

Run: `python -m pytest -q` e `ruff check .`
`git diff --stat main -- fixtures/pyspark/` tem que sair vazio.
