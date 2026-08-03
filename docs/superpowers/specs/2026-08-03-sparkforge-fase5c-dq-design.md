# SparkForge AWS — Fase 5c: SF-DQ, validação de dados como coisa lida

**Data:** 2026-08-03
**Status:** desenhado, não implementado.
**Depende de:** [Fase 4](2026-07-31-sparkforge-fase4-agentes-design.md) — coordenadores são onde a área nova se pendura ·
[Fase 5a](2026-08-01-sparkforge-fase5-emr-design.md) §3.1 — o critério de `runtime_scope` que esta fase obedece
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o ponto cego medido

`grep -ril "deequ\|great.expectations\|dbt"` sobre todo o repositório, excluindo
caches, devolve **um único arquivo**: a linha do `STATUS.md` que lista `SF-DQ`
como capacidade futura. Não há extrator, kind, regra, fixture, skill ou
coordenador. É folha em branco, não capacidade parcial.

O ponto cego não é acadêmico. Um job PySpark que valida dado tem hoje três
destinos possíveis dentro do motor, e nenhum deles é "foi analisado":

1. A validação é uma action Spark, e `SF-PY` a vê como action genérica — diz
   "há uma action aqui", nunca "esta action é uma validação, e ela está depois
   do write".
2. A validação roda e ninguém lê o resultado. Nenhum fact registra isso, então
   nenhuma regra pode acusá-lo. É o mesmo defeito de classe que a Fase 5b fechou
   com `SF-EMR-009` — mecanismo existindo sem garantia declarada — um nível
   acima: garantia que o **job do usuário** afirma ter e não tem.
3. A validação recomputa o lineage inteiro por rodar sobre DataFrame não
   persistido que será reusado. Custo real de execução, invisível ao catálogo.

## 2. Objetivo

Uma área `SF-DQ` que afirma sobre **cobertura e posicionamento** da validação de
dados dentro de um job PySpark, com facts próprios extraídos do mesmo `.py` que
o resto do motor já lê.

**Critério de sucesso central:** uma investigação sobre um job que valida dado
depois de escrevê-lo produz achado `SF-DQ` citando `fact_id`, e o mesmo job com
a validação antes do write não produz achado nenhum — golden bidirecional, como
toda regra do catálogo desde a Fase 0.

### Não-objetivos, com razão registrada

| Fora de escopo | Razão |
|---|---|
| Resultado de execução (`VerificationResult`, validation result do GE, `run_results.json` do dbt) | Vira relay de relatório alheio: a ferramenta **já disse** que o check falhou. O motor não acrescenta garantia nenhuma repetindo. O que ele acrescenta é afirmar sobre o que a ferramenta não vê — onde a validação está e se ela tem consequência |
| `great_expectations.yml` e expectation suites em JSON | Artefato declarativo fora do código, com parser próprio, e correlacionar suíte com a tabela que o job escreve exige casar por nome — heurística frágil. Fase própria, depois que os kinds `dq.*` existirem |
| dbt (`schema.yml`, `manifest.json`) | Mundo próprio, encosta no Spark só via `dbt-glue`/`dbt-spark`. Fase própria |
| Schema declarado (`StructType` contra `inferSchema`) | Cabe no motor e é barato, mas é contrato de leitura, não validação. Entra numa fase de schema, junto de `mergeSchema` |
| EMR Serverless e EMR on EKS | Dívida herdada da 5b, sem relação com esta fase |

## 3. Decisões de desenho

### D-1 — a área julga o processo, não o dado

`SF-DQ` afirma sobre a **suíte**: existe, onde está, tem consequência, quanto
custa. Não afirma que a coluna `cpf` tem nulo — isso é trabalho da ferramenta de
DQ, que já o faz melhor e com o dado na mão.

### D-2 — extrator próprio, não crescimento de `pyspark_ast`

`sparkforge/facts/data_quality.py`. `pyspark_ast.py` já tem 40 KB e 20 kinds; a
leitura de validação é responsabilidade separada, com framework próprio para
reconhecer. O custo aceito é caminhar a mesma AST duas vezes — o motor já
correlaciona facts entre extratores por posição, e é assim que `SF-DQ-001` vai
comparar a linha do check com a linha do `pyspark.write`.

### D-3 — fronteira com `SF-PY` por construção, não por supressão

`SF-DQ` só recebe gatilho que **exige saber que aquilo é validação**. Nenhuma
regra `SF-PY` é alterada, nenhum `absent:` é acrescentado a ela, e nenhuma
supressão cruzada entre áreas existe. Duplicação de achado fica impossível
porque as duas áreas afirmam coisas diferentes sobre a mesma linha — não porque
uma foi calada.

A alternativa recusada era `SF-PY` se calar quando a linha for validação. Ela
produz achado único e mais preciso, ao custo de acoplar duas áreas de catálogo —
exatamente o que a Fase 5a passou uma fase inteira desfazendo.

### D-4 — `dq.enforcement` é decidido pelo extrator

O gatilho de `SF-DQ-002` é a **ausência de consequência**, e consequência é
combinação de propriedades: o resultado precisa ser lido, e a leitura precisa
levar a aborto. O motor de hoje não compõe ausência de combinação —
`engine._absent_satisfied` só compara `kind`.

Segue-se o padrão que `SF-EMR-008` fixou na Fase 5b e que está escrito no
cabeçalho de `rules/catalog/emr-infra.yaml`: **se a resposta depende de mais de
uma propriedade, o extrator decide e emite**. `dq.enforcement` só é emitido
quando a consequência está presente e é coerente; consequência pela metade não
emite; o que não dá para ler vira `dq.unresolved`, contado e não presumido. A
regra usa `absent: dq.enforcement`.

Alargar `_absent_satisfied` foi recusado pelo mesmo motivo da 5b: o motor é
superfície de execução do catálogo inteiro, e cada alargamento vale para as 58
regras existentes.

### D-5 — coordenador próprio

`agents/data-quality-reviewer.md`, com `rule_areas: [SF-DQ]`, mais os espelhos
de plataforma. A alternativa era pendurar `SF-DQ` no `pyspark-code-reviewer`, já
que o artefato é o mesmo `.py`. Recusada por simetria de área: toda área do
catálogo tem coordenador identificável, e `tests/test_agent_coverage.py::test_no_area_is_orphan`
trata área sem coordenador como defeito. Área nova que se pendura em coordenador
alheio produz agente que faz duas coisas e skill que não sabe qual delas está
sendo pedida.

### D-6 — `runtime_scope: {}` nas quatro regras

O gatilho é AST. Não varia com versão de Glue, Spark, EMR ou Iceberg. É
literalmente o critério que a Fase 5a fixou: `runtime_scope` só é não-vazio
quando o gatilho genuinamente varia com a versão **e** essa versão vem do
runtime. A justificativa vai no cabeçalho do YAML, como a área `SF-EMR` fez.

## 4. Facts

### 4.1 Kinds emitidos

| Kind | Quando | Carrega |
|---|---|---|
| `dq.module_analyzed` | um `.py` foi lido | sentinela de execução do extrator. **Não serve de `requires_facts` para regra** — foi essa confusão que produziu o defeito de `SF-GLUE-002` na Fase 5a |
| `dq.check` | validação detectada | `framework` (`pydeequ`, `great_expectations`, `handmade`, `assert`), linha, função contentora, alvo quando resolvível, tipo do check |
| `dq.enforcement` | consequência presente **e** coerente | linha do check que ela protege, forma da consequência |
| `dq.unresolved` | leitura impossível | motivo, com a mesma disciplina de `pyspark.unresolved` e `athena.unresolved` |

`handmade` cobre o caso mais frequente em job Glue real: `df.filter(cond).count() > 0`
seguido de `raise`. Não é framework nenhum, e é validação.

### 4.2 Regras

| Regra | Gatilho | O que só `SF-DQ` enxerga |
|---|---|---|
| `SF-DQ-001` | `dq.check` com linha posterior ao `pyspark.write` do mesmo alvo | dado ruim já publicado quando a validação roda |
| `SF-DQ-002` | `dq.check` presente e `absent: dq.enforcement` | suíte roda, resultado não tem consumidor — garantia afirmada e inexistente |
| `SF-DQ-003` | `dq.check` sobre alvo sem `pyspark.cache` e com `pyspark.action` posterior sobre o mesmo alvo | validação recomputa o lineage |
| `SF-DQ-004` | dois ou mais `dq.check` sobre o mesmo alvo, cada um com action própria | N passadas onde uma agregação resolveria |

`SF-DQ-004` é a mais frágil das quatro e sabe disso: depende de resolver o alvo
por nome de variável, e o AST erra quando o DataFrame vem de parâmetro ou de
retorno de função. A resolução impossível vira `dq.unresolved`, nunca um alvo
adivinhado. Se a Task de pesquisa mostrar que a taxa de não-resolução é alta nas
fixtures reais, `SF-DQ-004` sai da fase em vez de entrar como regra que dispara
por acidente — decisão a tomar com número medido, não por gosto.

### 4.3 Premissas sob suspeita, a verificar antes de escrever código

A Fase 5b entrou com quatro candidatos de regra e três morreram na leitura das
fontes. O mesmo passo vem antes desta implementação, e três premissas deste
documento estão explicitamente marcadas como não verificadas:

1. **Great Expectations reescreveu a API pública na 1.0.** Detectar por
   `SparkDFDataset` e por métodos `expect_*` pode estar detectando só a linha
   0.18. Se a superfície da 1.x for outra, o reconhecimento de `framework:
   great_expectations` muda de forma, ou a fase entrega só `pydeequ` e
   `handmade` e registra o veto.
2. **PyDeequ** — se `VerificationSuite` continua a superfície de entrada, e
   quais versões de Spark a biblioteca ainda acompanha. Se ela não alcançar as
   versões que `GLUE_MATRIX` e `EMR_MATRIX` cobrem, a detecção continua válida
   (código legado existe) mas o `proposed_change` não pode recomendá-la.
3. **`assert` some sob `python -O`.** Se sumir, `dq.enforcement` derivado de
   `assert` afirma uma garantia que não existe no ambiente de produção — e a
   regra passaria a **calar** exatamente no caso em que deveria falar. Ou
   `assert` deixa de contar como consequência, ou conta com ressalva escrita
   dentro do achado. Decidir com a fonte na mão.

### 4.4 Como os gatilhos de 4.2 viram condição avaliável

Medido em `sparkforge/rules/engine.py` antes de escrever o plano: `_condition_candidates`
avalia **um fact por vez** — `where` e `expr` leem o contexto de um único fact — e
`_absent_satisfied` compara só `kind`. O motor **não** correlaciona dois facts.
"Linha do check posterior à linha do write" não é expressável como condição.

Isso não é obstáculo novo: é o mesmo limite que produziu D-4, e a resposta é a
mesma. O extrator caminha a AST inteira do módulo, então ele **já vê** os
`write`, os `cache` e os demais checks; a correlação é feita lá, e o catálogo lê
atributo de um fact só.

| Regra | Condição real no YAML |
|---|---|
| `SF-DQ-001` | `where: {attrs.position_vs_write: after_write}` |
| `SF-DQ-002` | `same_subject: true`, `dq.check` presente + `absent: dq.enforcement` |
| `SF-DQ-003` | `where: {attrs.target_persisted: false, attrs.action_after_check: true}` |
| `SF-DQ-004` | `expr: "measures.checks_on_target >= 2"` + `where: {attrs.shares_scan: false}` — **era `single_pass`**, nome aposentado por D-5c-1; corrigido aqui porque a Task 7 escreve o YAML copiando desta tabela |

`attrs.position_vs_write` tem três valores, nunca um booleano: `before_write`,
`after_write` e `no_write_in_module`. O terceiro é o caso em que o módulo valida
e não escreve — biblioteca de validação, ou job cujo write está noutro arquivo —
e ele **não é** `before_write`. Achatar os dois num booleano faria `SF-DQ-001`
calar por um motivo e o leitor entender outro.

`attrs.single_pass` é o que impede `SF-DQ-004` de acusar quem faz certo: uma
`VerificationSuite` do Deequ com cinco checks é **uma** passada por construção, e
sai com `single_pass: true`. Cinco `df.filter(...).count()` separados saem com
`false`. A regra separa as duas, que era o ponto.

> **Corrigido pela pesquisa de fontes.** O parágrafo acima afirma o que a fonte
> não sustenta, e o atributo mudou de nome. Ver §10, desvio D-5c-1.

Subject de `dq.enforcement` é **o mesmo** subject do check que ela protege —
`source_location` com o arquivo e a linha do check, sem `symbol`. É o que faz
`_subject_group_key` cair na mesma chave e `same_subject` funcionar em
`SF-DQ-002`. Enforcement com subject próprio faria a regra disparar sobre check
protegido, porque o `absent` seria avaliado num grupo onde a proteção não está.

## 5. Superfície e registro

Cada ponto abaixo foi medido no código, com `emr_cluster`/`SF-EMR` como caso de
referência. Esquecer um deles é o modo de falha desta fase:

| Onde | O quê |
|---|---|
| `sparkforge/facts/data_quality.py` | `EMITTED_KINDS` |
| `tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py` | `EXTRACTORS` — **duas adições manuais**, independentes |
| `sparkforge/adapters/cli.py`, `_core.py` | verbo `analyze data-quality` |
| `sparkforge/adapters/tools.py` | `sparkforge_analyze_data_quality` |
| `parity.yaml`, `manifest.json` | capacidade e tool declaradas |
| `scripts/regen_fixtures.py` | `regen_dq` e a entrada na lista |
| `rules/catalog/data-quality.yaml` | área, descoberta por glob |
| `agents/data-quality-reviewer.md` + espelhos | coordenador |
| `skills/review-data-validation/SKILL.md` + espelhos | skill do fluxo focado |

**Sem verbo `collect`.** O artefato é o `.py` do repositório, não API da AWS.

## 6. Prova

`fixtures/dq/`, oito casos com golden bidirecional:

| Fixture | Prova |
|---|---|
| `validation_after_write` | positivo de `SF-DQ-001` |
| `suite_without_enforcement` | positivo de `SF-DQ-002` |
| `check_recomputes_lineage` | positivo de `SF-DQ-003` |
| `repeated_checks_same_target` | positivo de `SF-DQ-004` |
| `validated_correctly` | negativo das quatro — valida antes do write, com consequência, sobre DF persistido |
| `pydeequ_suite` | mesmo kind saindo de framework diferente |
| `great_expectations_suite` | idem, e o caso que a premissa 4.3.1 pode reescrever |
| `unresolved_helper` | validação atrás de helper resolvido em runtime — `dq.unresolved`, sem alvo adivinhado |

Mais uma prova de ponta a ponta no molde de
`tests/test_emr_investigation_end_to_end.py`: um job real, sem flag de runtime,
produzindo achados `SF-DQ` e `SF-PY` **sobre a mesma linha sem se repetirem** —
que é a verificação de D-3.

## 7. Critérios de sucesso

1. `data_quality.py` emite os quatro kinds de 4.1, com `EMITTED_KINDS` declarado
2. As quatro regras de 4.2 existem, com `runtime_scope: {}` e justificativa no cabeçalho do YAML
3. Toda regra tem golden positivo **e** negativo
4. Todo kind emitido aparece em algum golden (`test_every_kind_of_every_extractor_appears_in_some_golden`)
5. `SF-DQ` tem coordenador, e `test_no_area_is_orphan` passa sem exceção declarada
6. Verbo CLI e tool MCP existem, e `parity.yaml` declara a capacidade nas cinco plataformas
7. A prova de ponta a ponta mostra achado `SF-DQ` e achado `SF-PY` sobre a mesma linha, sem duplicação semântica
8. As três premissas de 4.3 estão verificadas contra fonte oficial, com data, e o veto de qualquer uma delas registrado no cabeçalho do catálogo — não apagado
9. Nenhuma regra `SF-PY` existente muda de comportamento: os 17 goldens de `fixtures/pyspark/` continuam byte a byte iguais

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Reconhecimento por nome de método vira lista infinita de padrões | O extrator reconhece **forma** (chamada seguida de comparação seguida de aborto), não catálogo de nomes. O que não casar vira `dq.unresolved` |
| `SF-DQ-002` acusa job que valida em outro módulo | O achado declara o recorte: "sem consequência **neste corpus**", como `unreferenced_function_count` passou a fazer na 5b |
| Resolução de alvo por nome de variável erra e `SF-DQ-001` compara a linha errada | Alvo não resolvido não gera check com alvo — gera `dq.unresolved`. Regra que precisa de alvo não dispara sem alvo |
| A fase cresce para GE declarativo e dbt no meio da execução | Estão em não-objetivos com razão escrita. Entram em fase própria |

## 10. Desvios apurados pela pesquisa de fontes

A Task 0 do plano rodou antes de qualquer código, como a Fase 5b fez, e o
resultado está em [`knowledge/dq/validation-frameworks.md`](../../../knowledge/dq/validation-frameworks.md)
com URL e data por afirmação. Este documento **não é reescrito** — o registro do
que se pretendia tem valor próprio. Os desvios ficam aqui.

**D-5c-1 — `attrs.single_pass` afirmava o que a fonte não sustenta.** O artigo
original do Deequ (Schelter et al., PVLDB 2018, §4.1 e §5.1) descreve *scan
sharing por agrupamento*: métricas que não exigem re-particionamento cabem numa
passada; `isUnique`, `hasUniqueness` e entropia **pagam passada própria**. Uma
suíte com N checks custa uma passada **por agrupamento distinto**, não uma. O
exemplo canônico do próprio README do PyDeequ tem `isUnique("a")`.

O atributo passa a se chamar **`attrs.shares_scan`**, e afirma exatamente o que a
fonte autoriza: os checks deste fact compartilham varredura entre si. `handmade`
sai com `false` — cada `count()` é uma varredura própria, sem compartilhamento
nenhum. `pydeequ` sai com `true`. `SF-DQ-004` continua viável porque o contraste
que ela precisa sobrevive intacto: N passadas contra ≤ N, nunca "uma".

**D-5c-2 — `measures.declared_checks` sai.** Contar chamadas `addCheck` não conta
restrições: a forma oficial encadeia seis restrições dentro de **um** `addCheck`.
Nenhuma regra o consumia, e medida que não sustenta o próprio nome é a família de
defeito que a 5b corrigiu em `unreachable_function_count`. Não entra.

**D-5c-3 — `SparkDFDataset` está morto, e a detecção de GE muda de forma.**
`great_expectations/dataset/sparkdf_dataset.py` some na 1.0.0 (2024-08-22). A
detecção por métodos `expect_*` fica **vetada**: o prefixo sobrevive via
`Validator.__getattr__`, e o AST não sabe se a variável é um `Validator` — casar
por prefixo produziria falso positivo sobre qualquer objeto. O que sobra é
estreito e honesto: `batch_parameters={"dataframe": df}` expõe o DataFrame sob
chave literal, e é dali que sai `attrs.target`.

Consequência que precisa ser explícita: um `dq.check` de framework
`great_expectations` **não recebe** a chave `shares_scan`. Quantas expectativas
rodam vive no store do contexto, fora do `.py` — o extrator não sabe, e o motor
reprova caminho ausente em `where` (`engine._where_matches`), então `SF-DQ-004`
simplesmente não avalia esses checks. Ausência de chave é a forma de dizer "não
sei" sem que ninguém confunda com `false`.

**D-5c-4 — `assert` conta como consequência, com ressalva.** A referência da
linguagem confirma que `-O` apaga o `assert`, mas nenhuma fonte da AWS mostra
Glue ou EMR rodando o driver assim, e no Glue o caminho documentado
(`--customer-driver-env-vars`) **rejeita** chaves sem o prefixo `CUSTOMER_`. Logo
`form: "assert"` é enforcement legítimo, e a ressalva vai escrita dentro da
`explanation` de `SF-DQ-002` — não vira `dq.unresolved`, como o plano previa no
outro ramo.

**D-5c-10 — a correlação é por escopo, e `checks_on_target` conta por escopo.**
Medido na revisão da Task 2: indexar write, persist e action por **nome nu**
data o check de uma função contra o write de outra. Duas funções com um
parâmetro `vendas` cada produziam `after_write` sobre um DataFrame que nunca foi
escrito — acusação falsa, que é o modo de falha que o item 4 do
`rules/catalog/README.md` trata como pior que achado nenhum.

O índice passou a ser por escopo: corpo do módulo e cada `FunctionDef` /
`AsyncFunctionDef` separados. `measures.checks_on_target` foi junto, e isso
**contraria a letra da §4.4** deste documento, que diz "no módulo". A letra
estava errada pelo mesmo motivo: dois homônimos em escopos diferentes não são
dois checks sobre o mesmo alvo, e contá-los juntos faria `SF-DQ-004` afirmar
varredura repetida sobre dado que não é o mesmo.

Segunda decisão da mesma família: quando o nome do alvo é **religado** entre a
linha do check e a linha do write comparada, `attrs.position_vs_write` **não é
emitido** — chave ausente, nunca um quarto valor, no mecanismo já usado por
`shares_scan` em D-5c-3. `attrs.target_persisted`, ao contrário, sai `false` sob
religação em vez de ausente: ali a omissão calaria `SF-DQ-003`, e o rebind
viraria um jeito de sumir com a regra.

O preço, registrado: função que lê um DataFrame global perde a correlação com o
write do módulo e sai `no_write_in_module`. Erra para menos, que é o lado certo.

**D-5c-11 — o preço de D-5c-10 virado do avesso: parâmetro não afirma
persistência.** A revisão final da fase mediu que o preço acima **não** é sempre
"para menos". A forma canônica de biblioteca Glue — validar num helper, cachear
no chamador — produzia `target_persisted: false` e `action_after_check: true`, e
`SF-DQ-003` disparava sobre um DataFrame que está persistido:

```python
def valida(vendas):
    ruins = vendas.filter(vendas.valor < 0).count()
    vendas.write.parquet("s3://lake/curated/")

def main(spark):
    vendas = spark.read.parquet("s3://lake/raw/")
    vendas.cache()          # a persistência é real, e vive em OUTRO escopo
    valida(vendas)
```

Quando o alvo chega por **parâmetro** e não há nenhum evento de persistência no
próprio escopo, `attrs.target_persisted` **não é emitido**. Persistência de um
parâmetro é, por construção, evidência que vive fora do escopo: o índice não
pode vê-la, e `false` afirmaria o que ele não sabe. A exceção é ter evidência
local — `cache`/`persist`/`unpersist` sobre o parâmetro dentro da própria
função —, e aí a chave sai normalmente, inclusive `false`.

O preço, aceito e maior que o de D-5c-10: isto cala `SF-DQ-003` para **todo**
helper de validação, inclusive os genuinamente não persistidos. A alternativa
era acusar a forma canônica de biblioteca Glue.

`attrs.action_after_check` **continua** válido para parâmetro, e a assimetria é
real: a action posterior está dentro do escopo e é observada de fato. Só a
persistência vem de fora.

Correção de fato que este desvio arrasta: o cabeçalho de `data_quality.py`
afirmava que `action_after_check` era o único dos quatro do lado da acusação, e
que os outros três erravam "para menos". Medido, é falso — `SF-DQ-003` dispara
sobre `target_persisted: **false**`, então emitir `false` na ignorância empurra
para o disparo exatamente como emitir `true` sobre reuso. **Dois** atributos
estão do lado da acusação. O corolário que o texto também errava: para
`action_after_check`, ausência e `false` calam a regra **igualmente**, então o
argumento "a ausência calaria a regra" vale só para `target_persisted`.

**D-5c-12 — `dq.module_analyzed` É `requires_facts` de `SF-DQ-002`, e a §4.1
deste documento diz que não deveria.** O código está certo e o texto está
errado. A §4.1 proíbe em negrito, apontando para o defeito de `SF-GLUE-002` na
Fase 5a: sentinela de "algum arquivo foi lido" não é sentinela de "há o que
julgar aqui", então a regra passa a barreira, avalia, dá falso e some de
findings **e** de skipped ao mesmo tempo. `data-quality.yaml:201` usa a
sentinela mesmo assim, e o motivo é o `absent:` de `SF-DQ-002`: a disciplina do
`rules/catalog/README.md` exige que regra de ausência declare um fact que prove
que o extrator rodou, senão ela dispara sobre corpus vazio. O modo de falha de
`SF-GLUE-002` **não existe aqui** porque `dq.check` também está em
`requires_facts`, e ele já prova que há validação a julgar — a sentinela responde
só por "o extrator rodou", que é a pergunta que o `absent:` precisa fazer.

**D-5c-13 — `framework` tem três valores, não quatro.** A §4.1 lista `pydeequ`,
`great_expectations`, `handmade` e `assert`. O extrator emite os três primeiros.
`assert` nunca foi framework de validação: é **forma de consequência**, e virou
`attrs.form` de `dq.enforcement`, junto de `raise` e `sys.exit`. O lugar está
certo — o que `assert` responde é "o que acontece quando o check acusa", e não
"quem fez o check".

**D-5c-5 — `proposed_change` que recomende suíte precisa de guarda de versão.**
PyDeequ não alcança Glue 3.0 nem nenhuma release EMR 6.x (piso Python 3.9), e o
Spark 3.4 não está no mapa de `pydeequ/configs.py`. GX 1.x exige Python ≥ 3.10.
Recomendação genérica de "use uma suíte" seria conselho impossível de seguir em
metade das releases que o repo cobre; a `proposed_change` aponta para
`knowledge/dq/validation-frameworks.md`, onde o alcance está medido.
