# Frameworks de validação de dados em PySpark — o que a fonte oficial diz

Esta página existe por um motivo único: a §4.3 do
[spec da Fase 5c](../../docs/superpowers/specs/2026-08-03-sparkforge-fase5c-dq-design.md)
marcou **três premissas como não verificadas**, e a Fase 5b provou que essa etapa
mata candidatos. Cada afirmação abaixo tem URL e `retrieved:`. Onde a fonte
contrariou o spec, a conclusão está escrita como **veto**, com o motivo — a §4 é
o bloco que vai para o cabeçalho de `rules/catalog/data-quality.yaml`.

**Coleta desta rodada: 2026-08-03.**

Regra desta página, herdada do [`INDEX.md`](../INDEX.md): o que não foi
encontrado em fonte oficial está escrito como **não encontrado**, não como
inferência. Argumento por ausência está marcado como tal, com a página que foi
lida.

---

## 0. Os três veredictos, em uma linha cada

| # | Premissa da §4.3 do spec | Veredicto | Consequência imediata |
|---|---|---|---|
| 1 | GE reescreveu a API pública na 1.0; detectar por `SparkDFDataset` e `expect_*` pode estar detectando só a 0.18 | **Confirmada — a premissa do spec estava certa e a detecção antiga está morta na 1.x** | `SparkDFDataset` não existe mais no pacote. Detecção por ele marca código 0.x, e só. `proposed_change` nunca pode citá-lo |
| 2 | PyDeequ: `VerificationSuite` continua a entrada, e o alcance de versões | **Entrada confirmada; alcance com dois buracos medidos** | Spark 3.4 **não** é suportado (EMR 6.12.0–6.15.0), e Python < 3.9 também não (toda a série EMR 6.x e Glue 3.0) |
| 3 | `assert` some sob `python -O` | **Confirmada na linguagem; `-O` por padrão em Glue/EMR: NÃO ENCONTRADO em fonte oficial** | `assert` conta como consequência, **com ressalva escrita dentro do achado** — que é o segundo ramo previsto pelo próprio spec |

Um sub-veredicto adicional, que a pesquisa produziu e o spec não pedia:
`attrs.single_pass` como "uma `VerificationSuite` com N checks é uma passada só"
é **falso como escrito**. A fonte primária diz outra coisa, mais fraca e
suficiente. Ver §2.3.

---

## 1. Great Expectations

### 1.1 `SparkDFDataset` e os métodos `expect_*` sobre um DataFrame — MORTOS na 1.x

O módulo que hospedava `SparkDFDataset` era
`great_expectations/dataset/sparkdf_dataset.py`. Ele **existe** na última 0.18 e
**não existe** na 1.0.0 nem na release corrente:

| Tag | `great_expectations/dataset/sparkdf_dataset.py` |
|---|---|
| `0.18.22` | HTTP 200 — presente |
| `1.0.0` | HTTP 404 — ausente |
| `1.19.1` | HTTP 404 — ausente |

> Verificado por `raw.githubusercontent.com/great-expectations/great_expectations/{tag}/great_expectations/dataset/sparkdf_dataset.py` (retrieved 2026-08-03).

E a listagem do pacote na release corrente não tem diretório `dataset` nenhum —
tem `expectations`, `validator`, `execution_engine`, `checkpoint`, `core`,
`data_context`, `datasource`, `metrics`, `render`, `types`, `experimental`,
`compatibility`, `exceptions`, `self_check`.

> https://api.github.com/repos/great-expectations/great_expectations/contents/great_expectations?ref=1.19.1 (retrieved 2026-08-03)

`1.0.0` foi publicada em **2024-08-22**.

> https://api.github.com/repos/great-expectations/great_expectations/releases/tags/1.0.0 (retrieved 2026-08-03)

O guia oficial de migração V0→V1 confirma o corte na direção certa, sem nomear a
classe: o padrão de chamar expectativa direto sobre o objeto de dado foi
substituído por Suite e Validation Definition explícitas; `Profilers` e o
conceito de `batch request` foram removidos.

> GX V0 to V1 Migration Guide. https://docs.greatexpectations.io/docs/0.18/reference/learn/migration_guide/ (retrieved 2026-08-03)

**Ressalva medida, para não exagerar o veto.** `expect_*` como *nome de método*
não desapareceu do código-fonte: `Validator.__getattr__`, em `1.19.1`, ainda
resolve dinamicamente qualquer nome que comece com `expect_` e esteja no
registro de expectativas:

```python
# great_expectations/validator/validator.py, tag 1.19.1, linha ~413
    def __getattr__(self, name):
        ...
        if (
            name.startswith("expect_") or name == "unexpected_rows_expectation"
        ) and get_expectation_impl(name):
            return self.validate_expectation(name)
```

> https://raw.githubusercontent.com/great-expectations/great_expectations/1.19.1/great_expectations/validator/validator.py (retrieved 2026-08-03)

Isso **não** ressuscita a detecção. O que o AST vê é `alguma_variavel.expect_x(...)`,
e a chamada só é validação se `alguma_variavel` for um `Validator` — que o AST
não sabe. Sobre um `pyspark.sql.DataFrame` puro, `expect_*` nunca existiu:
`SparkDFDataset` era um *wrapper* em volta do DataFrame, e é ele que sumiu.
Reconhecer por prefixo de nome de método é exatamente o "catálogo infinito de
nomes" que o Risco 1 da §8 do spec proíbe.

### 1.2 A forma canônica de validar um DataFrame Spark hoje

A documentação corrente (1.19.1) descreve o caminho assim:

```python
import great_expectations as gx

context = gx.get_context()
data_source = context.data_sources.add_spark(name="my_data_source")
data_asset = data_source.add_dataframe_asset(name="my_dataframe_data_asset")
batch_definition = data_asset.add_batch_definition_whole_dataframe("my_batch_definition")

dataframe = spark.read.csv(csv, header=True, inferSchema=True)
batch_parameters = {"dataframe": dataframe}

validation_definition = context.validation_definitions.get("my_validation_definition")
validation_results = validation_definition.run(batch_parameters=batch_parameters)
```

> Connect to DataFrames. https://docs.greatexpectations.io/docs/core/connect_to_data/dataframes/ (retrieved 2026-08-03)

As expectativas são **classes**, não métodos:

```python
from great_expectations import expectations as gxe

preset_expectation = gxe.ExpectColumnMaxToBeBetween(
    column="passenger_count", min_value=1, max_value=6, severity="warning"
)
```

> Create an Expectation. https://docs.greatexpectations.io/docs/core/define_expectations/create_an_expectation (retrieved 2026-08-03) — "All Expectations are found in the `gx.expectations` module."

E existe um caminho interativo, mais curto e igualmente documentado:

```python
validation_results = batch.validate(expectation)
```

> Test an Expectation. https://docs.greatexpectations.io/docs/core/define_expectations/test_an_expectation (retrieved 2026-08-03)

**O que isso significa para a detecção estática**, escrito antes de a Task 3
começar: no caminho canônico, o DataFrame **é** visível no AST — ele aparece
como valor sob a chave literal `"dataframe"` de um dict passado em
`batch_parameters=`. Mas *quais* e *quantas* expectativas rodam **não** está no
`.py`: `context.validation_definitions.get("nome")` é uma busca por string num
store do contexto GX (`great_expectations.yml` e suites em JSON), que a §2 do
spec pôs explicitamente **fora de escopo** desta fase. O caminho `batch.validate(...)`
é a exceção — ali a expectativa é um literal no código.

Consequência para a Task 3, Step 4: há detecção possível, e ela é parcial por
construção. O módulo permite afirmar "há validação GE aqui, sobre este alvo";
não permite afirmar quantos checks nem se é uma passada. `measures.declared_checks`
e `attrs.single_pass` **não** podem ser preenchidos para `great_expectations` a
partir do `.py`, e o que não puder ser lido é `dq.unresolved` contado, nunca
presumido.

### 1.3 O nome do pacote importado

Continua `great_expectations`. O nome de distribuição é `great-expectations`; o
import documentado é `import great_expectations as gx`.

> https://pypi.org/project/great-expectations/ (retrieved 2026-08-03)

### 1.4 Alcance: a 1.x não instala em metade das releases que este repo cobre

Metadados da release corrente (`1.19.1`, publicada em **2026-07-24**):

- `requires_python`: `<3.14,>=3.10`
- extra `spark`: `pyspark<4.2,>=2.3.2`

> https://pypi.org/pypi/great-expectations/json (retrieved 2026-08-03)

O extra `spark` cobre **toda** a faixa de Spark que `GLUE_MATRIX` e `EMR_MATRIX`
conhecem (3.1.1 a 3.5.6). Quem exclui é o Python:

| Runtime | Python do PySpark | GX 1.19.1 instala? |
|---|---|---|
| Glue 3.0 | 3.7 | **não** |
| Glue 4.0 | 3.10 | sim |
| Glue 5.0 / 5.1 | 3.11 | sim |
| EMR 6.4.0–6.15.0 | não documentado pela AWS; interpretadores instalados são 2.7 e 3.7 | **não** — nenhum dos dois alcança o piso 3.10 |
| EMR 7.0.0–7.12.0 | 3.9 (default) | **não no default**; 3.11 está instalado, então alcança se `PYSPARK_PYTHON` apontar para ele |
| EMR 7.13.0 | 3.11 | sim |

> Colunas de Python conforme [`../emr/runtime-matrix.md`](../emr/runtime-matrix.md) §4.1 e `GLUE_MATRIX` em `sparkforge/facts/runtime_detect.py`.

### 1.5 Vetos de Great Expectations

- **V-GE-1.** Não reconhecer `framework: great_expectations` por `SparkDFDataset`
  como se fosse a API corrente. A classe não existe desde a `1.0.0` (2024-08-22).
  Se um `.py` a usa, ele é código 0.x, e um achado pode dizer isso — mas
  `proposed_change` **nunca** pode recomendá-la.
- **V-GE-2.** Não reconhecer validação por método com prefixo `expect_` sobre uma
  variável qualquer. O prefixo sobrevive no `Validator` por `__getattr__`, e o
  AST não sabe se a variável é um `Validator`. Detectar por nome de método erra
  nos dois sentidos.
- **V-GE-3.** Não emitir `measures.declared_checks` nem `attrs.single_pass` para
  `great_expectations`. No caminho canônico as expectativas vivem no store do
  contexto, fora do `.py`, e nenhuma fonte oficial declara quantas passadas uma
  validação GE faz sobre o dado.
- **V-GE-4.** Não recomendar GE 1.x para Glue 3.0, EMR 6.x, nem para EMR
  7.0.0–7.12.0 sem trocar `PYSPARK_PYTHON` — o piso é Python 3.10.

---

## 2. PyDeequ

### 2.1 `VerificationSuite(spark).onData(df)...run()` continua a entrada — CONFIRMADO

Release corrente: **1.6.0**, publicada em **2026-07-08**. `requires_python`
`<4,>=3.9`. `pyspark<4.0.0,>=2.4.7` como extra opcional (`pip install pydeequ[pyspark]`).

> https://pypi.org/pypi/pydeequ/json (retrieved 2026-08-03)

O quickstart oficial do repositório:

```python
check = Check(spark, CheckLevel.Warning, "Review Check")

checkResult = VerificationSuite(spark) \
    .onData(df) \
    .addCheck(
        check.hasSize(lambda x: x >= 3) \
        .hasMin("b", lambda x: x == 0) \
        .isComplete("c")  \
        .isUnique("a")  \
        .isContainedIn("a", ["foo", "bar", "baz"]) \
        .isNonNegative("b")) \
    .run()
```

> https://github.com/awslabs/python-deequ (retrieved 2026-08-03), e o mesmo bloco no blog da AWS: https://aws.amazon.com/blogs/big-data/testing-data-quality-at-scale-with-pydeequ/ (post de 2020-12-30, atualizado em 2024-06; retrieved 2026-08-03)

**Detalhe que contradiz um teste já escrito no plano.** A Task 3, Step 2 do plano
propõe `measures.declared_checks = methods.count("addCheck")`. A forma oficial
usa **um único `addCheck`** com seis restrições encadeadas dentro dele. Contar
`addCheck` conta *objetos `Check`*, não *restrições*, e no exemplo canônico o
número seria `1` para seis regras. Ou o nome do measure passa a dizer o que ele
de fato conta (`declared_check_objects`), ou o extrator conta as restrições
encadeadas dentro do argumento. Decidir na Task 3, com o exemplo acima na mão.

**Nota operacional.** PyDeequ exige a variável de ambiente `SPARK_VERSION`; sem
ela levanta erro em vez de adivinhar:

> "SPARK_VERSION environment variable is required. Supported values are: {keys}"
> — `pydeequ/configs.py`, tag `v1.6.0`

### 2.2 Alcance de versões, contra `GLUE_MATRIX` e `EMR_MATRIX`

A lista de versões suportadas não está no README — está no código, como um mapa
de Spark para coordenada Maven do JAR do Deequ:

| Chave (Spark major.minor) | Coordenada |
|---|---|
| `3.5` | `com.amazon.deequ:deequ:2.0.8-spark-3.5` |
| `3.3` | `com.amazon.deequ:deequ:2.0.8-spark-3.3` |
| `3.2` | `com.amazon.deequ:deequ:2.0.8-spark-3.2` |
| `3.1` | `com.amazon.deequ:deequ:2.0.8-spark-3.1` |

> `SPARK_TO_DEEQU_COORD_MAPPING` em https://raw.githubusercontent.com/awslabs/python-deequ/v1.6.0/pydeequ/configs.py (retrieved 2026-08-03). Versão fora do mapa levanta: "Found incompatible Spark version {version}; Use one of the Supported Spark versions for Deequ: {keys}".

**Spark 3.4 não está no mapa.** Não é omissão de documentação: é a chave que não
existe no dicionário, e o código levanta erro em vez de escolher a vizinha.

Cruzando com as duas matrizes do repositório:

| Runtime | Spark | Spark ok? | Python do PySpark | Python ok (≥3.9)? | PyDeequ 1.6.0 alcança? |
|---|---|---|---|---|---|
| Glue 3.0 | 3.1.1 | sim | 3.7 | não | **não** |
| Glue 4.0 | 3.3.0 | sim | 3.10 | sim | sim |
| Glue 5.0 | 3.5.4 | sim | 3.11 | sim | sim |
| Glue 5.1 | 3.5.6 | sim | 3.11 | sim | sim |
| EMR 6.4.0–6.5.0 | 3.1.2 | sim | 2.7 / 3.7 instalados | não | **não** |
| EMR 6.6.0–6.7.0 | 3.2.x | sim | 2.7 / 3.7 instalados | não | **não** |
| EMR 6.8.0–6.11.1 | 3.3.x | sim | 2.7 / 3.7 instalados | não | **não** |
| EMR 6.12.0–6.15.0 | 3.4.x | **não** | 2.7 / 3.7 instalados | não | **não, por dois motivos** |
| EMR 7.0.0–7.13.0 | 3.5.x | sim | 3.9 (3.11 em 7.13.0) | sim | sim |

Resumo do buraco: **toda a série EMR 6.x está fora**, e quatro releases dela
(6.12.0 a 6.15.0) estariam fora mesmo com Python novo, porque rodam Spark 3.4.
Glue 3.0 está fora pelo Python.

### 2.3 Uma `VerificationSuite` com N checks é uma passada só? — PARCIALMENTE, e a premissa como escrita é FALSA

Esta é a resposta que a §4.4 do spec chama de fundamento de `attrs.single_pass`.

As páginas de produto da AWS não respondem: dizem "an optimized set of
aggregation queries" e "translates your test description into a series of Spark
jobs", que é o oposto de uma garantia de passada única.

> https://aws.amazon.com/blogs/big-data/testing-data-quality-at-scale-with-pydeequ/ (retrieved 2026-08-03)
> https://aws.amazon.com/blogs/big-data/test-data-quality-at-scale-with-deequ/ (retrieved 2026-08-03)

Quem responde é o artigo original do Deequ, da Amazon, no VLDB 2018 — e responde
com uma condição, não com um "sim":

> "For all metrics that do not require re-partitioning the data, the runner collects their required aggregation functions and executes them in a single generated SparkSQL query over the data to benefit from scan-sharing. In our example from Section 3.1, such metrics would be the `Size` of the dataset, the `Completeness` of six columns, as well as the `Compliance` for the three `satisfies` constraints. **All these metrics will be computed simultaneously in a single pass over the data.**"
> — §4.1, p. 1787

> "Optimizations. During the computation of multiple metrics, we apply a set of manually enforced query optimizations: (a) we cache the result of the count operation on dataframes, as many metrics require the size of the delta for example; (b) **we apply scan sharing for aggregations: we run all aggregations that rely on the same grouping (or no grouping) of the data in the same pass over the data.**"
> — §4.1, p. 1788

> "The plot labeled 'no grouping' refers to the results for computing a set of six metrics (size of the data and completeness of five columns) which do not require us to re-partition the data. Therefore these metrics can be computed by aggregations in a single pass over the data. **The remaining lines refer to the computation of metrics such as entropy and uniqueness on the columns brand, material and product id, which require us to repartition the data.**"
> — §5.1, p. 1789

> Schelter, Lange, Schmidt, Celikel, Bießmann, Grafberger. *Automating Large-Scale Data Quality Verification*. PVLDB 11(12):1781–1794, 2018. https://www.vldb.org/pvldb/vol11/p1781-schelter.pdf (retrieved 2026-08-03)

**O que a fonte autoriza, exatamente:** uma `VerificationSuite` custa **uma
passada por agrupamento distinto** exigido pelas suas restrições, não uma passada
por restrição. Restrições sem agrupamento — `hasSize`, `isComplete`,
`isNonNegative`, `isContainedIn`, `satisfies` — cabem todas na mesma passada.
Restrições que exigem re-particionamento — `isUnique`/`hasUniqueness`,
entropia, distintos — pagam passada própria.

**O que a fonte não autoriza:** dizer que uma suíte com N checks é *uma* passada.
Não é, quando há `isUnique` no meio. E o exemplo canônico do README da AWS tem
`isUnique("a")` — ou seja, o próprio quickstart oficial é um caso de mais de uma
passada.

**Isso não mata `SF-DQ-004`**, e é importante ser preciso sobre por quê: o
contraste que a regra precisa continua de pé. N `df.filter(...).count()`
separados são N passadas por construção; uma suíte com os mesmos N checks é, no
pior caso, o número de agrupamentos distintos, que é ≤ N e na prática muito
menor. A regra separa as duas coisas, que era o ponto da §4.4 do spec.

**Mas obriga a mudar a redação e o nome.** `single_pass: true` afirma algo que a
fonte não sustenta. O atributo precisa afirmar o que é verdade — que a suíte
compartilha varredura entre checks — e a `explanation` da regra não pode dizer
"é uma passada por construção".

### 2.4 Vetos de PyDeequ

- **V-DQ-1.** `attrs.single_pass: true` como "N checks, uma passada" é falso. A
  garantia da fonte é *scan sharing por agrupamento*: uma passada por agrupamento
  distinto. Renomear para algo que não minta (`shares_scan`, ou
  `single_pass_per_grouping`) ou documentar a semântica exata no extrator, e
  ajustar a `explanation` de `SF-DQ-004`.
- **V-DQ-2.** `proposed_change` não pode recomendar PyDeequ para Glue 3.0 nem
  para nenhuma release EMR 6.x. Em 6.12.0–6.15.0 há dois impedimentos
  independentes (Spark 3.4 fora do mapa, e Python instalado abaixo de 3.9).
  Recomendação genérica de "use uma suíte de passada única" precisa da guarda de
  versão — é o que a `proposed_change` de `SF-DQ-004` já aponta para esta página.
- **V-DQ-3.** Contar `addCheck` não conta restrições. A forma oficial encadeia
  seis restrições dentro de um `addCheck`.

---

## 3. `assert` sob `python -O`

### 3.1 A linguagem: confirmado, e sem ambiguidade

> "In the current implementation, the built-in variable `__debug__` is `True` under normal circumstances, `False` when optimization is requested (command line option `-O`). **The current code generator emits no code for an `assert` statement when optimization is requested at compile time.**"
> — The Python Language Reference, `assert` statement

> https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement (retrieved 2026-08-03)

E há duas portas para ligar isso:

> `-O` — "Remove assert statements and any code conditional on the value of `__debug__`."
> `PYTHONOPTIMIZE` — "If this is set to a non-empty string it is equivalent to specifying the `-O` option."

> https://docs.python.org/3/using/cmdline.html (retrieved 2026-08-03)

Ou seja: a variável de ambiente basta. Não é preciso alterar a linha de comando.

### 3.2 AWS Glue roda o driver com `-O`? — NÃO ENCONTRADO, e há um indício contrário

A página que enumera **todos** os parâmetros de job reconhecidos pelo Glue foi
lida inteira. Ela não tem `PYTHONOPTIMIZE`, não tem `-O`, e não descreve como o
processo Python do driver é lançado.

> Using job parameters in AWS Glue jobs. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-glue-arguments.html (retrieved 2026-08-03)

Isto é argumento por ausência, e está marcado como tal. O que **é** afirmação
positiva na mesma página, e aponta na direção contrária: o único mecanismo
documentado para o usuário injetar variável de ambiente no driver é
`--customer-driver-env-vars`, e ele **rejeita** chaves sem o prefixo `CUSTOMER_`:

> "Each key must have the `CUSTOMER_ prefix`. For example: for `"CUSTOMER_KEY3=VAL3,KEY4=VAL4"`, `KEY4=VAL4` will be ignored and not set."

`PYTHONOPTIMIZE` não tem o prefixo. Pelo caminho documentado, o usuário de Glue
**não consegue** ligar `-O` por variável de ambiente de job.

### 3.3 Amazon EMR roda o driver com `-O`? — NÃO ENCONTRADO, mas é ligável

A página de configuração do Spark no EMR lista os defaults que a AWS sobrescreve
(`spark.executor.memory`, `spark.dynamicAllocation.enabled`, dois de pushdown no
metastore) e as classificações disponíveis. Não menciona `PYTHONOPTIMIZE`, `-O`
nem otimização de bytecode Python.

> Configure Spark. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-configure.html (retrieved 2026-08-03)

Diferença relevante em relação ao Glue: a classificação `spark-env` "sets values
in the `spark-env.sh` file" — isto é, o EMR **tem** um caminho documentado para
definir variáveis de ambiente arbitrárias do Spark (é por ele que se define
`PYSPARK_PYTHON`, conforme [`../emr/runtime-matrix.md`](../emr/runtime-matrix.md) §4.1).
Nada na documentação diz que a AWS define `PYTHONOPTIMIZE` ali por padrão; o que
se pode afirmar é que **um operador poderia** definir.

### 3.4 Conclusão, e a ressalva que precisa ir dentro do achado

O spec previu dois ramos. O ramo que a fonte selecionou é o segundo:

> "Se rodarem, `assert` **não** é consequência; se não rodarem, é consequência
> com ressalva escrita dentro do achado."

Nenhuma fonte oficial mostra Glue ou EMR rodando o driver com `-O` ou com
`PYTHONOPTIMIZE` definido. Sem isso, vale o comportamento padrão do
interpretador: `__debug__` é `True` e o `assert` executa. Portanto
`form: "assert"` **é** emitido como `dq.enforcement`, e o Step 3 da Task 4 do
plano — que previa `dq.unresolved` com `reason: "assert_stripped_under_O"` — não
se aplica.

A ressalva é obrigatória, e não é decoração: ela cobre o que o motor não pode
ver. `PYTHONOPTIMIZE` é fato de **ambiente**, e a Fase 5c lê apenas o `.py`.
Um enforcement por `assert` é, com precisão, "consequência que existe salvo se o
interpretador rodar otimizado — condição que este corpus não permite verificar".
Texto a levar para a `explanation` de `SF-DQ-002` e/ou para o achado:

> A consequência aqui é um `assert`. O interpretador Python remove todo `assert`
> quando roda com `-O` ou com `PYTHONOPTIMIZE` definido, e nesse caso a proteção
> desaparece sem aviso. Nenhuma documentação de Glue ou EMR indica que o driver
> rode assim por padrão, e no Glue o único mecanismo documentado de variável de
> ambiente do driver exige o prefixo `CUSTOMER_`, que impede definir
> `PYTHONOPTIMIZE`. Ainda assim, isto é ambiente, e este achado leu apenas o
> código: `raise` com exceção explícita não depende de nenhuma dessas condições.

### 3.5 Vetos de `assert`

- **V-AS-1.** Não emitir `dq.unresolved` com `reason: "assert_stripped_under_O"`
  como se `-O` fosse o padrão. Nenhuma fonte oficial sustenta que Glue ou EMR
  rodem o driver otimizado, e afirmar isso faria a regra **calar** justamente no
  caso em que deve falar.
- **V-AS-2.** E não fazer o inverso: `assert` como enforcement sem a ressalva
  escrita. A garantia é condicional a um fato de ambiente que esta fase não lê.

---

## 4. Bloco de vetos, para o cabeçalho de `rules/catalog/data-quality.yaml`

Copiar daqui, não reescrever de memória. Cada item existe porque uma fonte
contrariou uma premissa; apagá-los é convidar a reinvenção da premissa morta.

```
# VETOS APURADOS NA PESQUISA DE FONTES (2026-08-03).
# Detalhe e URLs: knowledge/dq/validation-frameworks.md
#
# V-GE-1  SparkDFDataset nao existe desde great_expectations 1.0.0 (2024-08-22):
#         great_expectations/dataset/ foi removido do pacote. Detectar por ele
#         marca codigo 0.x; proposed_change NUNCA pode recomenda-lo.
# V-GE-2  Nao reconhecer validacao por metodo com prefixo `expect_`. O prefixo
#         sobrevive no Validator via __getattr__, e o AST nao sabe se a variavel
#         e um Validator. Sobre um DataFrame puro, expect_* nunca existiu.
# V-GE-3  Nao emitir declared_checks nem single_pass para great_expectations:
#         no caminho canonico as expectativas vivem no store do contexto, fora
#         do .py, e nenhuma fonte declara quantas passadas uma run GE faz.
# V-GE-4  GX 1.x exige Python >= 3.10: nao recomendar em Glue 3.0, EMR 6.x, nem
#         EMR 7.0.0-7.12.0 sem trocar PYSPARK_PYTHON para o 3.11 instalado.
#
# V-DQ-1  "VerificationSuite com N checks e UMA passada" e FALSO. A fonte
#         primaria (VLDB 2018, secoes 4.1 e 5.1) garante scan sharing por
#         AGRUPAMENTO: uma passada por agrupamento distinto. isUnique e
#         entropia exigem re-particionamento e pagam passada propria -- e o
#         quickstart oficial do PyDeequ contem isUnique. O contraste com N
#         count() separados continua valido; a redacao "uma passada por
#         construcao" nao.
# V-DQ-2  PyDeequ 1.6.0 mapeia Spark 3.1/3.2/3.3/3.5 e exige Python >= 3.9.
#         Spark 3.4 NAO esta no mapa (EMR 6.12.0-6.15.0). Toda a serie EMR 6.x
#         e Glue 3.0 ficam de fora pelo Python. proposed_change com guarda.
# V-DQ-3  Contar chamadas `addCheck` nao conta restricoes: a forma oficial
#         encadeia varias restricoes dentro de UM addCheck.
#
# V-AS-1  `assert` NAO e removido por padrao em Glue nem em EMR: nenhuma fonte
#         oficial mostra o driver rodando com -O ou com PYTHONOPTIMIZE, e no
#         Glue o unico mecanismo documentado de env var do driver exige prefixo
#         CUSTOMER_, que impede definir PYTHONOPTIMIZE. Logo assert CONTA como
#         dq.enforcement.
# V-AS-2  ... com ressalva escrita dentro do achado: -O e fato de AMBIENTE, e
#         esta area le apenas o .py. `raise` nao tem essa condicional.
```

---

## Fontes

**Great Expectations**

- Connect to DataFrames (forma canônica de validar DataFrame Spark). https://docs.greatexpectations.io/docs/core/connect_to_data/dataframes/ (retrieved 2026-08-03)
- Create an Expectation (expectativas são classes em `gx.expectations`). https://docs.greatexpectations.io/docs/core/define_expectations/create_an_expectation (retrieved 2026-08-03)
- Test an Expectation (`batch.validate(expectation)`). https://docs.greatexpectations.io/docs/core/define_expectations/test_an_expectation (retrieved 2026-08-03)
- GX V0 to V1 Migration Guide. https://docs.greatexpectations.io/docs/0.18/reference/learn/migration_guide/ (retrieved 2026-08-03)
- Metadados da distribuição (`requires_python`, extra `spark`, versão 1.19.1 de 2026-07-24). https://pypi.org/pypi/great-expectations/json (retrieved 2026-08-03)
- Listagem do pacote na tag 1.19.1 — sem diretório `dataset`. https://api.github.com/repos/great-expectations/great_expectations/contents/great_expectations?ref=1.19.1 (retrieved 2026-08-03)
- Presença/ausência de `great_expectations/dataset/sparkdf_dataset.py` nas tags `0.18.22` (200), `1.0.0` (404) e `1.19.1` (404), via `raw.githubusercontent.com` (retrieved 2026-08-03)
- `Validator.__getattr__` resolvendo `expect_*` em 1.19.1. https://raw.githubusercontent.com/great-expectations/great_expectations/1.19.1/great_expectations/validator/validator.py (retrieved 2026-08-03)
- Data de publicação da 1.0.0. https://api.github.com/repos/great-expectations/great_expectations/releases/tags/1.0.0 (retrieved 2026-08-03)

**PyDeequ / Deequ**

- Repositório e quickstart. https://github.com/awslabs/python-deequ (retrieved 2026-08-03)
- Metadados da distribuição (1.6.0 de 2026-07-08, `requires_python <4,>=3.9`, extra `pyspark`). https://pypi.org/pypi/pydeequ/json (retrieved 2026-08-03)
- `SPARK_TO_DEEQU_COORD_MAPPING` e mensagens de erro, tag `v1.6.0`. https://raw.githubusercontent.com/awslabs/python-deequ/v1.6.0/pydeequ/configs.py (retrieved 2026-08-03)
- Testing data quality at scale with PyDeequ (AWS Big Data Blog, 2020-12-30, atualizado 2024-06). https://aws.amazon.com/blogs/big-data/testing-data-quality-at-scale-with-pydeequ/ (retrieved 2026-08-03)
- Test data quality at scale with Deequ (AWS Big Data Blog). https://aws.amazon.com/blogs/big-data/test-data-quality-at-scale-with-deequ/ (retrieved 2026-08-03)
- Schelter et al., *Automating Large-Scale Data Quality Verification*, PVLDB 11(12):1781–1794, 2018 — §4.1 (scan sharing) e §5.1 (grouping exige re-particionamento). https://www.vldb.org/pvldb/vol11/p1781-schelter.pdf (retrieved 2026-08-03)

**`assert` e `-O`**

- The Python Language Reference — the `assert` statement. https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement (retrieved 2026-08-03)
- Python — Command line and environment (`-O`, `PYTHONOPTIMIZE`). https://docs.python.org/3/using/cmdline.html (retrieved 2026-08-03)
- Using job parameters in AWS Glue jobs — lista completa de parâmetros; sem `PYTHONOPTIMIZE`, e regra do prefixo `CUSTOMER_` em `--customer-driver-env-vars`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-glue-arguments.html (retrieved 2026-08-03)
- Configure Spark (Amazon EMR) — classificações, incluindo `spark-env`; sem menção a `PYTHONOPTIMIZE` ou `-O`. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-configure.html (retrieved 2026-08-03)

**Matrizes deste repositório, usadas nas comparações de alcance**

- [`../emr/runtime-matrix.md`](../emr/runtime-matrix.md) — `EMR_MATRIX`, incluindo a coluna "Python do PySpark" e a nota de que a AWS não a documenta para a série 6.x.
- `GLUE_MATRIX` em [`../../sparkforge/facts/runtime_detect.py`](../../sparkforge/facts/runtime_detect.py) — Glue 3.0/4.0/5.0/5.1.

**Não encontrado, e registrado como tal**

- Nenhuma documentação oficial da AWS declara que o driver Python de Glue ou de EMR rode com `-O` ou com `PYTHONOPTIMIZE` definido por padrão. As duas páginas lidas para chegar a essa conclusão estão citadas acima. Não inferir o contrário sem fonte nova.
- Nenhuma fonte oficial declara quantas passadas sobre o dado uma execução de validação do Great Expectations faz. `attrs.single_pass` não tem fundamento para esse framework.
- O README do PyDeequ **não** declara as versões de Spark suportadas; a única declaração é o mapa em `configs.py`, citado acima.
