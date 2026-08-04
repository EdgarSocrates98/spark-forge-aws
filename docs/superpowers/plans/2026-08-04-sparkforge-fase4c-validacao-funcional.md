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

**A Task 1 mediu, confirmou e decidiu.** Ver a tabela dos quatro eixos e os
desvios `D-4c-1` a `D-4c-3` na própria task: nenhum dos 102 kinds dos 16
extratores nomeia chave de negócio; contagem, schema e agregados são deriváveis,
e o eixo de chaves entra **declarado e marcado como tal**.

---

## Task 1: o que é derivável, medido — e o que fazer com as chaves — **CONCLUÍDA**

Antes de qualquer código. É a Task 0 de pesquisa em outra forma: aqui a fonte é o
próprio repositório, e a Fase 4b provou que essa medição muda o desenho.

**Files:** nenhum. Produz medição e decisão, escritas no plano.

**Método:** `EMITTED_KINDS` lido por **import** dos módulos de
`sparkforge/facts/` — **16 módulos, 102 kinds** —, e o payload de cada kind
medido pelo mapa `kind -> {measures, attrs}` construído sobre os
`expected/facts.json` de **todas** as fixtures do repositório, mais execução dos
extratores sobre fonte sintética onde a fixture não cobria a forma. Nenhuma
resposta abaixo vem de grep sobre o código.

- [x] **Step 1: Para cada um dos quatro eixos, responda com evidência**

| Eixo | Fact produtor | O que ele carrega **exatamente** | Veredito |
|---|---|---|---|
| **Contagem** | `pyspark.write` | `attrs {mode, target}`. O **nome** do alvo, forma tabela e forma caminho | **Derivável** |
| **Schema** | `catalog.table_schema` | `attrs.column_types {coluna: tipo}` — nome **e** tipo, verbatim; `attrs.partition_keys [nomes]`; `measures {column_count, partition_key_count}` | **Derivável, com nome e tipo** |
| **Chaves** | **nenhum** | os sete candidatos dão booleano, contagem, ou coluna de outra natureza — detalhe abaixo | **Não derivável** — depende de entrada do operador |
| **Agregados** | `catalog.table_schema` | as colunas numéricas saem de `attrs.column_types`, com o tipo declarado que **escolhe o modo de comparação** da D-4 | **Derivável, com o tipo junto** |

**Contagem.** O check precisa da **identidade do alvo**, não do valor — o valor
vem do resultado que o operador produz. `pyspark.write` dá o alvo nas duas
formas, medido sobre fonte sintética:
`{"mode": "overwrite", "target": "db.vendas"}`,
`{"mode": "append", "target": "s3://bucket/curated/vendas/"}`,
`{"mode": "overwritePartitions", "target": "cat.db.tbl"}`, e
`{"target": "db.outro"}` — **`mode` pode faltar** (`insertInto`), então o plano
não pode depender dele. O subject é `source_location` (symbol = função
envolvente), então o alvo mora em `attrs` e o casamento com `catalog.*`/
`iceberg.*` é por **string** contra o `subject.symbol` deles, que é
`{type: "table", symbol: "db.eventos"}`. Nome de três partes (`cat.db.tbl`)
contra símbolo de catálogo de duas (`db.tbl`) **não casa**: vira
`funcval.unresolved`, nunca alvo adivinhado.

**Schema.** `catalog_schema.py:134-156` (`_column_types`) copia o tipo declarado
**sem normalizar** — `decimal(18,2)` sobrevive —, e funde `columns` com
`partition_keys` (`setdefault`, `columns` vence). Medido na fixture
`catalog/glue_table_schema`:
`{"cliente_id": "bigint", "valor": "double", "dt": "string"}`.
É o único lugar do repositório onde coluna e tipo aparecem juntos.

**Fronteira que essa derivação NÃO autoriza:** o plano usa o catálogo para saber
**quais** colunas e tipos existem; o comparador compara **antes contra depois**,
nunca resultado contra catálogo. Comparar o observado com o declarado é a
asserção absoluta que a §2 do spec põe fora de escopo — e seria `SF-DQ`, não
`SF-FVAL`. Ver desvio D-4c-3.

**Chaves — a varredura completa, e o que cada candidato realmente carrega:**

| Candidato | O que carrega | Por que não serve |
|---|---|---|
| `pyspark.join` | `measures.on_arity` | Número, e **menos do que o plano supunha**: `pyspark_ast.py:723-730` lê `node.args[1]`, então `df.join(dim, on=["a","b"])` — forma com keyword — emite `measures {}`, nem o número sai. Medido. E chave de join não é chave do resultado |
| `pyspark.dedup` | `attrs {has_explicit_columns: bool}` | `dropDuplicates(["pedido_id"])` vira `true`. O subset **é** a chave de fato, e `pyspark_ast.py:325` descarta os nomes |
| `pyspark.window` | `attrs {has_partition_by, has_order_by, has_frame}` | Três booleanos. O `partitionBy` do latest-per-key é chave, e some |
| `plan.join` | `attrs {join_type, strategy, build_side, has_condition}` | Nenhuma coluna |
| `plan.exchange` | `attrs.partitioning` | Só o **nome** da estratégia (`"hashpartitioning"`); `spark_plan.py:830-843` descarta o conteúdo do parêntese |
| `sql.predicate(.enriched)` | `attrs.column` | Nomeia coluna — de **filtro**, e do lado da leitura |
| `sql.projection(.enriched)` | `measures.column_count` | Número |

**Nenhum fact do repositório nomeia chave de negócio.** Confirma e endurece a
correção que abriu este plano.

**Agregados.** O check precisa de nome de coluna numérica **e** do tipo, porque
o tipo é o que decide exata contra tolerante (D-4 do spec).
`catalog.table_schema.attrs.column_types` dá os dois: `valor: double` vira
`agg:sum:valor` comparado com tolerância, `cliente_id: bigint` vira
`agg:sum:cliente_id` comparado exato. Rejeitado para este eixo:
`sql.projection`, que só conta colunas (`measures.column_count`), medido na
execução do extrator sobre `SELECT loja_id, sum(valor) AS total_valor, ...` —
sai `{"column_count": 3}` e nenhum nome.

**Quase-produtores rejeitados, com o motivo gravado:**

| Candidato | Eixo que ele quase serve | Por que **não** |
|---|---|---|
| `catalog.table_partitions` | chaves | Mede `partition_count`, `distinct_values`, `avg_bytes_per_partition` e **nenhum nome**. Na fixture `catalog/glue_table_schema`, `db.eventos` tem `partition_count: 1200` e `distinct_values: 1200` sobre a coluna `dt` — 1200 valores para **todas** as linhas da tabela. Um check de unicidade sobre `dt` acusaria P0 em dado correto, por construção do particionamento |
| `catalog.table_schema.attrs.partition_keys` | chaves | É o mesmo erro **com nomes** — `["dt"]`. Que o fact nomeie a coluna não a torna chave, e o nome disponível é justamente o que torna a tentação plausível |
| `iceberg.files_summary.measures.total_records` | contagem | Parece contagem de linhas e não é: `iceberg_metadata.py:294-310` soma `record_count` só da seção `files`; `delete_files` é seção **separada** (`iceberg.delete_files_summary`). Em tabela com delete files, `total_records` conta linha já apagada. E ainda seria a contagem de um snapshot de metadata, não da execução que o operador rodou |
| `dq.check` | chaves, e o eixo inteiro | Já medido e rejeitado na Fase 4b — está escrito em `routing.yaml:59-60`. `check_type` medido nas fixtures: `verification_suite`, `count_of_violations`, `batch_parameters_dataframe` — a forma do framework, nunca uma chave |

- [x] **Step 2: Decida o eixo de chaves, com o custo dos dois caminhos**

**Decisão: o eixo de chaves não entra no plano derivado. Entra por declaração
explícita do operador, marcada como declarada.**

Três partes:

1. **Sem `--key`, o plano não pede check de chave — e diz isso.** `funcval.plan`
   carrega `undeclared_axes: ["keys"]` com a razão em texto. Ausência **escrita**,
   não silêncio: mesma disciplina de `dq.unresolved` e `bench.unresolved`.
2. **Com `funcval plan --key <col>[,<col>]`**, o check entra com
   `origin: "declared"` e `derived_from: []`, ao lado dos derivados, que trazem
   `origin: "derived"` e o `fact_id`. O campo `origin` existe em **todo** check,
   inclusive nos derivados — se aparecesse só no caso feio, seria exceção, e
   exceção não é procedência.
3. **`SF-FVAL-003` nasce com produtor:** o `funcval.check_delta` do check de
   chave, declarado ou trazido pelo resultado como não planejado — a §10 do spec
   já obrigou o comparador a **reportar** o não planejado em vez de ignorá-lo.

| Caminho | Ganho | Custo medido |
|---|---|---|
| **A — o operador declara** *(escolhido)* | As cinco regras da §6 nascem com produtor; a fixture `duplicate_key_appeared` sobrevive | O plano deixa de ser 100% derivado. Exige `origin` em todo check e `derived_from: []` no declarado. Uma flag nova em `funcval plan`, que as **quatro** listas de `test_adapters_tools.py` e o `regen_funcval` têm que carregar. E chave declarada **errada** produz P0 em dado correto — o mesmo modo de falha do proxy de partição, com a diferença que decide: a afirmação é do operador, fica gravada no plano e é auditável, em vez de o motor adivinhar |
| **B — partição como proxy** | Custo zero de superfície | **Rejeitado, e com número:** ver a linha de `catalog.table_partitions` acima. `distinct_values = partition_count = 1200` para a tabela inteira. Acusaria dado correto |
| **C — sem eixo de chaves nesta fase** | Plano 100% derivado, procedência trivial | `SF-FVAL-003` ficaria sem produtor e a fase entregaria **quatro** regras contra as cinco da §6 — quebra o critério 2 da §9. E deixaria uma pergunta P0 sem caminho nenhum, existindo um caminho honesto |

**O precedente que decide entre A e C** é `sparkforge/facts/consumers.py`: o
único extrator do pacote que lê "um arquivo que uma pessoa escreveu", e a
docstring dele dá o argumento inteiro — quem consome uma tabela "é conhecimento
da organização", e derivar de proxy faria invisível virar "sem consumidor", "a
resposta errada com cara de resposta certa". Chave de negócio é da mesma
natureza, e a partição como proxy é exatamente essa resposta errada. O
repositório **já aceita** entrada declarada como fact de primeira classe. O que
ele nunca aceitou é entrada declarada **sem rótulo de procedência** — e é isso
que o campo `origin` paga.

**Variante considerada e rejeitada:** `.sparkforge/keys.yaml`, no molde de
`consumers.yaml`, que daria ao declarado um artefato com `artifact_sha256`.
Rejeitada por custo (formato, extrator, fixtures — numa fase de sete tasks) e
por volatilidade: inventário de consumidor é estável e versionável; chave de
validação é por alvo e por mudança. E o registro existe mesmo assim —
`funcval plan --out` escreve o plano, e `funcval compare --plan` o relê como
artefato.

- [x] **Step 3: Meça também o que o resultado do operador precisa carregar**

Derivado regra a regra da §6 do spec:

| Regra | O que ela precisa ler | Campo do resultado |
|---|---|---|
| `SF-FVAL-001` contagem | Um número por lado | `checks["count"].value` — inteiro |
| `SF-FVAL-002` schema — coluna ausente, tipo mudado | O **mapa** coluna→tipo por lado. `column_count` não distingue coluna removida de coluna renomeada, e a regra fala das duas | `checks["schema"].value` — objeto `{coluna: tipo}` |
| `SF-FVAL-003` chave duplicada depois e não antes | Um número por lado, e a distinção entre "zero duplicatas" e "não medi" | `checks["key:<c1>+<c2>"].value` — inteiro: quantos **valores** de chave ocorrem mais de uma vez |
| `SF-FVAL-004` agregado fora da tolerância | Um número por lado **e** o tipo, que escolhe exata contra tolerante | `checks["agg:sum:<coluna>"].value`; o **tipo vem do plano**, não do resultado |
| `SF-FVAL-005` cobertura | O conjunto de checks que vieram contra o que o plano pediu, e "não veio" ≠ "veio zero" | A **presença da chave** em `checks` |

**Contrato mínimo — cinco regras:**

1. **`target`** (string, obrigatório). Resultado com `target` diferente do plano
   não é comparação: é `funcval.unresolved`. Comparar números de tabelas
   diferentes é pior que não comparar.
2. **`checks`** (objeto, obrigatório). A **presença da chave** é o sinal de
   cobertura. Zero é `{"value": 0}`; não medido é a chave **ausente**. É a mesma
   regra que `benchmark.py` fixou — "presença é por CHAVE, não por kind" — e pelo
   mesmo motivo: chave ausente é como este motor diz "não sei".
3. Cada check é **objeto**, não valor nu: `{"value": <número|objeto|null>}`. O
   objeto existe para caber o item 4.
4. **`value: null` exige `unavailable_reason`.** É o terceiro estado: "rodei e
   não consegui" não é "não reportei" nem "deu zero". Vira `funcval.unresolved`
   e **não** conta como reportado para a `SF-FVAL-005`.
5. **O modo de comparação vem do plano, nunca do resultado** — senão o operador
   escolhe se o próprio número é comparado exato ou com tolerância. `type` no
   resultado só é lido para check que o plano **não** pediu.

Opcionais: `plan_ref` (o `fact_id` do `funcval.plan`, no molde do
`benchmark_ref` de `_core.py:1566`), `side` (`"before"`/`"after"` — quando
presente e contradizendo a flag do CLI, vira `funcval.unresolved` em vez de
comparação invertida) e `type` por check, com o item 5.

Resultado válido:

```json
{
  "target": "db.vendas",
  "plan_ref": "f_3a91c2",
  "side": "before",
  "checks": {
    "count":              {"value": 1000},
    "schema":             {"value": {"cliente_id": "bigint",
                                     "valor": "double",
                                     "dt": "string"}},
    "agg:sum:valor":      {"value": 1000000.0},
    "agg:sum:cliente_id": {"value": 88123},
    "key:pedido_id":      {"value": 0},
    "agg:sum:desconto":   {"value": null,
                           "unavailable_reason": "coluna ausente no ambiente de origem"}
  }
}
```

Neste exemplo: `key:pedido_id` **rodou e deu zero duplicatas**;
`agg:sum:desconto` **rodou e não deu**; e um check que o plano pediu e não
aparece em `checks` **não foi reportado**. Os três são estados distintos, e
`SF-FVAL-005` conta só o terceiro como cobertura faltante — os dois primeiros
viram `funcval.unresolved`.

### Desvios medidos — texto pronto para a §11 do spec

O spec **não é reescrito**: ganha uma §11 "Desvios medidos antes da
implementação", como a §8 da Fase 4b. Aplicá-la é trabalho da Task 7.

**D-4c-1 — `pyspark.join` não dá as chaves, e dá menos do que a §4 supunha.** A
D-1 afirma que "`pyspark.join` dá as chaves". Não dá: o fact carrega
`measures.on_arity` — o **número** de colunas do `on` — e nunca os nomes. E há
menos que isso: `pyspark_ast.py:723-730` lê `node.args[1]`, então a forma com
keyword (`df.join(dim, on=["a","b"])`) não emite medida alguma. A varredura dos
102 kinds dos 16 extratores confirmou que **nenhum** fact nomeia chave de
negócio; os candidatos (`pyspark.dedup`, `pyspark.window`, `plan.join`,
`plan.exchange`, `sql.predicate`, `sql.projection`) carregam booleano, contagem
ou coluna de outra natureza. Contagem, schema e agregados seguem deriváveis, e
os agregados saem melhor do que a D-1 previa: `catalog.table_schema` dá coluna
**e tipo**, que é o que a D-4 precisa para escolher o modo de comparação.

**D-4c-2 — o eixo de chaves entra por declaração marcada, não por derivação.**
Consequência do D-4c-1. Sem `--key`, o plano não pede check de chave e
**declara o vazio**: `funcval.plan` carrega `undeclared_axes: ["keys"]` com a
razão. Com `funcval plan --key <col>[,<col>]`, o check entra com
`origin: "declared"` e `derived_from: []`; todo check derivado carrega
`origin: "derived"` e o `fact_id`. A D-1 continua valendo para os três eixos
deriváveis; para o quarto, a procedência passa a dizer **que é declarada** em
vez de calar. Partição como proxy foi medida e rejeitada: na fixture
`catalog/glue_table_schema`, `db.eventos` tem `distinct_values = partition_count
= 1200` sobre `dt` para a tabela inteira — um check de unicidade ali acusaria
dado correto.

**D-4c-3 — o comparador nunca compara o resultado contra o catálogo.** O schema
declarado deriva **quais** colunas e tipos existem, e nada mais. A comparação é
sempre antes contra depois. Comparar o observado com o declarado é a asserção
absoluta que a §2 já pôs fora de escopo, e é pergunta de `SF-DQ` — o critério 10
da §9 depende disso valer também dentro do comparador, não só entre as áreas.

- [x] **Step 4: Commit da medição**

---

## Task 2: `funcval plan` — **CONCLUÍDA**

**Files:**
- Create: `sparkforge/facts/funcval.py`, `tests/test_facts_funcval.py`

- [x] **Step 1: O teste que falha**

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

- [x] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_facts_funcval.py -v`
Expected: FAIL — `ModuleNotFoundError`. Obtido: `ModuleNotFoundError: No module
named 'sparkforge.facts.funcval'`, erro de coleta, zero teste rodado.

- [x] **Step 3: Implemente**

Módulo no padrão de `benchmark.py`: `EXTRACTOR_ID`, `EMITTED_KINDS` com os
**quatro** kinds da §5 do spec (`funcval.plan`, `funcval.check_delta`,
`funcval.analyzed`, `funcval.unresolved`), asserção final de namespace,
`sort_facts` no retorno.

`build_plan(facts, keys=(), path_hint="")` deriva o que a Task 1 mediu ser
derivável, e só isso:

- **contagem** — `checks["count"]`, de `pyspark.write.attrs.target`;
- **schema** — `checks["schema"]`, de `catalog.table_schema` do alvo casado;
- **agregados** — `checks["agg:sum:<coluna>"]` para cada coluna numérica de
  `catalog.table_schema.attrs.column_types`, cada uma com o `type` declarado, que
  é o que a Task 3 usa para escolher exata contra tolerante;
- **chaves** — nada, a menos que `keys` venha do `--key`. Sem ele,
  `attrs.undeclared_axes = ["keys"]` com a razão em texto: nenhum dos 102 kinds
  nomeia chave de negócio (D-4c-1, D-4c-2).

Cada check carrega `origin` — `"derived"` com o `fact_id` de origem, ou
`"declared"` com `derived_from: []`. O campo existe nos **dois** casos; se
aparecesse só no declarado, seria exceção, e exceção não é procedência.

Alvo sem write vira `funcval.unresolved`, nunca alvo adivinhado. Alvo de três
partes contra símbolo de catálogo de duas também: `funcval.unresolved`, não
casamento por prefixo.

- [x] **Step 4: Rode e commite**

`tests/test_facts_funcval.py`: 39 passed. Suíte: **3644 passed / 5 skipped**
(era 3605/5 — as 39 são as novas). `ruff check .` limpo.

### Desvios medidos na implementação — texto para a §11 do spec

**D-4c-4 — um `funcval.plan` por alvo distinto, e a medição que obrigou a
decidir.** A Task 1 não decidiu o caso de vários `pyspark.write` no mesmo corpus.
Medido: as **sete** fixtures do repositório que emitem `pyspark.write` emitem
**uma** cada, então nenhuma exercita o caso — mas `pyspark_ast.extract_path`
sobre **um** arquivo com cinco writes emite **5 facts e 4 alvos distintos**
(`db.vendas` duas vezes por `saveAsTable` e `insertInto`, `db.clientes`,
`cat.db.tbl`, e um caminho `s3://`), e o corpus do verbo é um **arquivo de
facts**, que é a união de tudo que o operador extraiu. O caso é alcançável.
Decisão: **um plano por alvo**. As chaves de `checks` (`count`, `schema`,
`agg:sum:<coluna>`) não têm namespace de alvo e colidiriam; o contrato do
resultado fixa `target` como string **singular** e resultado com alvo diferente é
`funcval.unresolved`, então um plano com N alvos obrigaria a comparação a
**escolher**; e o subject por alvo (`{type: "table", symbol: <alvo>}`) já separa
os `Fact.id`. O mesmo alvo escrito duas vezes continua sendo **um** plano, com os
dois `fact_id` em `derived_from` — presença por chave, não por fact.

**D-4c-5 — `attrs.target` do `pyspark.write` é melhor-esforço do AST e pode não
nomear alvo nenhum.** Medido em `fixtures/pyspark/clean_job`:
`df.write.mode("overwrite").partitionBy("data_pedido").parquet(saida)` emite
`target: "data_pedido"` — o argumento do `partitionBy`, porque o do `.parquet()`
é variável (`pyspark_ast.py:661` cai no primeiro literal da cadeia fora do
`.mode()`). O plano **não** tenta corrigir: o alvo entra verbatim e o casamento
estrito o transforma em `catalog_schema_unmatched`, que é o sinal visível de que
o nome não descreve tabela nenhuma. Adivinhar aqui produziria plano de agregados
sobre colunas de outra tabela. Corrigir na origem é outra fase.

**D-4c-6 — `undeclared_axes` não é campo do eixo de chaves; é do plano.** A
Task 1 o desenhou para as chaves. Medido na implementação que ele mente se for só
delas: alvo que não casa com o catálogo não tem check de schema **nem** de
agregado, e listar só `["keys"]` ali seria meia-verdade — o plano estaria calando
dois eixos enquanto declara um. Então `undeclared_axes` é computado do que
faltou, com `undeclared_axes_reason` por eixo. Nas sete fixtures reais com write,
**todas** saem com `["aggregates", "keys", "schema"]`: nenhuma junta hoje um
`pyspark.write` e um `catalog.table_schema` do **mesmo** alvo. A Task 5 tem que
construir esse corpus, senão o eixo de schema e o de agregados nunca aparecem em
golden.

**D-4c-7 — tipo de coluna que o módulo não classifica vira `unresolved`, não
silêncio.** As fixtures exercitam três tipos (`bigint`, `double`, `string`). O
módulo classifica pelo vocabulário de Hive/Glue e pelo de
`DataType.simpleString`, sobre a **cabeça** do tipo (`decimal(18,2)` →
`decimal`), e guarda o declarado verbatim. O que não está em nenhuma das duas
listas não vira agregado **e não some**: vira `column_type_unclassified`. Sem
isso, um tipo desconhecido reduziria a cobertura do eixo de agregados com cara de
cobertura completa — o defeito que a `SF-FVAL-005` existe para acusar.

**D-4c-8 — o check de `schema` no plano não carrega o mapa coluna→tipo do
catálogo.** Aplicação da D-4c-3 **dentro** do plano: se o plano levasse o mapa
declarado junto, a Task 3 teria contra o que conferir o observado, e a asserção
absoluta entraria pela porta dos fundos. O check carrega `origin`, `type` e
`derived_from`, e nada mais; o valor vem sempre do resultado. Pelo mesmo motivo,
chave declarada **não** é conferida contra o schema do catálogo — `--key
coluna_que_nao_existe` entra no plano sem `unresolved`, porque a afirmação é do
operador e julgá-la seria `SF-DQ`.

**D-4c-9 — dois `catalog.table_schema` distintos para o mesmo símbolo não
escolhem um.** Um arquivo de facts pode unir dois dumps de catálogo. Facts
idênticos (mesmo `Fact.id`) são o mesmo dump lido duas vezes e não são
ambiguidade; dois facts **distintos** para o mesmo símbolo são, e escolher entre
eles seria chute com cara de derivação. Vira `catalog_schema_ambiguous`, e os
eixos de schema e agregados ficam declarados como ausentes.

---

## Task 3: `funcval compare`

**Files:**
- Modify: `sparkforge/facts/funcval.py`, `tests/test_facts_funcval.py`

- [ ] **Step 1: O teste que falha**

```python
def _plano(**checks):
    return {"target": "t", "checks": checks}


def _resultado(**checks):
    return {"target": "t", "checks": checks}


def test_contagem_divergente_vira_check_delta():
    facts = build_comparison(
        _plano(count={"origin": "derived", "type": "bigint", "derived_from": ["f_1"]}),
        _resultado(count={"value": 1000}),
        _resultado(count={"value": 998}),
    )
    delta = [f for f in facts if f.kind == "funcval.check_delta"][0]
    assert delta.attrs["check"] == "count"
    assert delta.attrs["diverged"] is True


def test_float_dentro_da_tolerancia_nao_diverge():
    """Soma de float depende da ordem de reducao: um repartition legitimo muda o
    total nos ultimos bits. Comparacao exata daria falso positivo justamente na
    mudanca que a fase existe para aprovar."""
    plano = _plano(**{"agg:sum:valor": {"origin": "derived", "type": "double",
                                        "derived_from": ["f_2"]}})
    facts = build_comparison(
        plano,
        _resultado(**{"agg:sum:valor": {"value": 1_000_000.0}}),
        _resultado(**{"agg:sum:valor": {"value": 1_000_000.000001}}),
    )
    assert [f for f in facts if f.kind == "funcval.check_delta"][0].attrs["diverged"] is False


def test_inteiro_e_comparado_exato():
    facts = build_comparison(
        _plano(count={"origin": "derived", "type": "bigint", "derived_from": ["f_1"]}),
        _resultado(count={"value": 1000}),
        _resultado(count={"value": 1001}),
    )
    assert [f for f in facts if f.kind == "funcval.check_delta"][0].attrs["diverged"] is True


def test_o_tipo_vem_do_plano_e_nao_do_resultado():
    """Se o resultado escolhesse o modo, o operador decidiria se o proprio numero
    e comparado exato ou com tolerancia. Contrato minimo, regra 5."""
    plano = _plano(**{"agg:sum:n": {"origin": "derived", "type": "bigint",
                                    "derived_from": ["f_3"]}})
    facts = build_comparison(
        plano,
        _resultado(**{"agg:sum:n": {"value": 1_000_000, "type": "double"}}),
        _resultado(**{"agg:sum:n": {"value": 1_000_001, "type": "double"}}),
    )
    assert [f for f in facts if f.kind == "funcval.check_delta"][0].attrs["diverged"] is True


def test_check_do_plano_ausente_no_resultado_e_contado():
    """Validacao parcial lida como aprovacao e o encontro de 'nenhum problema'
    com 'nao coletei'. SF-FVAL-005 le esta contagem."""
    plano = _plano(
        count={"origin": "derived", "type": "bigint", "derived_from": ["f_1"]},
        schema={"origin": "derived", "type": "schema", "derived_from": ["f_4"]},
    )
    facts = build_comparison(plano, _resultado(count={"value": 1}),
                             _resultado(count={"value": 1}))
    sentinela = [f for f in facts if f.kind == "funcval.analyzed"][0]
    assert sentinela.measures["planned_check_count"] == 2
    assert sentinela.measures["reported_check_count"] == 1


def test_valor_nulo_com_razao_nao_e_zero_nem_ausencia():
    """O terceiro estado do contrato: 'rodei e nao consegui'. Vira unresolved e
    NAO conta como reportado."""
    plano = _plano(count={"origin": "derived", "type": "bigint", "derived_from": ["f_1"]})
    facts = build_comparison(
        plano,
        _resultado(count={"value": None, "unavailable_reason": "tabela indisponivel"}),
        _resultado(count={"value": 10}),
    )
    assert [f for f in facts if f.kind == "funcval.check_delta"] == []
    assert [f for f in facts if f.kind == "funcval.unresolved"]
    sentinela = [f for f in facts if f.kind == "funcval.analyzed"][0]
    assert sentinela.measures["reported_check_count"] == 0
```

O formato de `plano`, `antes` e `depois` é o contrato que a Task 1 Step 3 fixou.
`target` divergente entre plano e resultado é `funcval.unresolved`, não
comparação — e isso também merece teste.

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

`funcval plan --facts <arquivo> [--key <col>[,<col>]] --out <arquivo>` e
`funcval compare --plan <arquivo> --before <arquivo> --after <arquivo>`.

O `--key` é o que a Task 1 Step 2 decidiu (D-4c-2): repetível, e o check que ele
cria entra com `origin: "declared"`. Sem ele, `funcval.plan` sai com
`undeclared_axes: ["keys"]` — o eixo ausente fica **escrito**.

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

A Task 1 decidiu (D-4c-2) que o eixo de chaves entra **declarado**:
`duplicate_key_appeared` **fica**, e o golden dele tem que mostrar o check com
`origin: "declared"` e `derived_from: []` — se o golden não distinguir declarado
de derivado, a procedência mente e a fixture prova a coisa errada.

`partial_coverage` carrega os **três** estados do contrato num caso só: um check
que veio com zero, um que veio `null` com `unavailable_reason`, e um que o plano
pediu e não apareceu. Só o terceiro é cobertura faltante; os dois primeiros são
`funcval.unresolved`. É a fixture que cobre esse kind.

Uma fixture a mais, do plano e não da comparação: `plan_sem_chave` — plano
derivado sem `--key`, com `undeclared_axes: ["keys"]` na saída. É o que prova que
o eixo ausente fica escrito em vez de calado.

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
de diferença. A de `003` diz que a chave é **declarada pelo operador**, não
derivada de fact nenhum (D-4c-2) — achado P0 sobre chave errada é chave errada
declarada, e quem lê precisa saber disso para julgar o achado.

`SF-FVAL-003` dispara no gatilho **estrito** da §6: `antes == 0` e `depois > 0`.
Duplicata que já existia e **cresceu** (`depois > antes > 0`) não é o gatilho
escrito, e transformá-la em P0 aqui seria afirmar sobre o dado, não sobre a
mudança. O `funcval.check_delta` carrega os dois valores de qualquer forma, então
o caso fica visível sem virar achado inventado.

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
