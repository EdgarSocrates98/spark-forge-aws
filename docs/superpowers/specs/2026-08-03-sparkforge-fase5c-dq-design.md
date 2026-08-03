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
| `SF-DQ-004` | `expr: "measures.checks_on_target >= 2"` + `where: {attrs.single_pass: false}` |

`attrs.position_vs_write` tem três valores, nunca um booleano: `before_write`,
`after_write` e `no_write_in_module`. O terceiro é o caso em que o módulo valida
e não escreve — biblioteca de validação, ou job cujo write está noutro arquivo —
e ele **não é** `before_write`. Achatar os dois num booleano faria `SF-DQ-001`
calar por um motivo e o leitor entender outro.

`attrs.single_pass` é o que impede `SF-DQ-004` de acusar quem faz certo: uma
`VerificationSuite` do Deequ com cinco checks é **uma** passada por construção, e
sai com `single_pass: true`. Cinco `df.filter(...).count()` separados saem com
`false`. A regra separa as duas, que era o ponto.

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
