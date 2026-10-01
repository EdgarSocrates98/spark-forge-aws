# SparkForge AWS — Fase 4c: validação funcional automatizada

**Data:** 2026-08-04
**Status:** **implementado e fechado em 2026-08-04**, na branch `feat/fase4c-funcval`.
Este documento **não foi reescrito**: ele é registro do que se pretendia na data
acima. Onde a implementação divergiu, a §11 registra a divergência e **este
documento perde** para [`../STATUS.md`](../STATUS.md).
**Fecha:** o **último** dos quatro itens de rigor da §16 do
[spec da Fase 0](2026-07-29-sparkforge-fase0-design.md).
**Base:** [Fase 4a](2026-08-03-sparkforge-fase4a-benchmark-design.md) fixou o
padrão do módulo derivado; [Fase 4b](2026-08-04-sparkforge-fase4b-gates-assinatura-design.md)
deixou o gate esperando por esta fase.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: um gate que já sabe o nome do seu produtor

`rules/catalog/routing.yaml` declara, hoje:

```yaml
functional_validation_defined:
  advisory_reason: "sem produtor ate a Fase 4c"
```

A Fase 4b fixou o critério de que **gate só endurece com produtor declarado**, e
deixou este advisory por não ter um. Quando esta fase entregar o produtor, aquele
gate endurece **declarando `satisfied_by`** — sem tocar em nada da 4b. Era a
propriedade que o critério prometia, e ela cobra agora.

E o nome do gate diz **qual** produtor: `functional_validation_**defined**` —
*definida*, não *executada*. O que satisfaz o gate é o **plano**, e isso não é
detalhe de vocabulário. Definir o que validar **antes** de mudar o código é o que
impede escolher, depois, o check que passa.

A Fase 4a fechou a outra metade do par: o benchmark prova que ficou mais rápido.
Falta provar que continua certo.

## 2. Objetivo

Uma área `SF-FVAL` que afirma sobre **equivalência antes e depois de uma
mudança** — contagem, schema, chaves e agregados —, a partir de um plano que o
motor deriva dos facts que já tem e de um resultado que o operador produz.

**Critério de sucesso central:** um par de resultados de validação — antes e
depois — produz achado citando `fact_id` quando algum proxy diverge, e não produz
achado nenhum quando os quatro batem; e `functional_validation_defined` passa a
poder endurecer.

### Não-objetivos, com razão registrada

| Fora de escopo | Razão |
|---|---|
| **Executar as consultas** | O motor lê artefato e julga. Executar exigiria cluster, credencial e orçamento, e faria a suíte depender de infraestrutura — a mesma fronteira que a 4a recusou atravessar |
| Gerar script PySpark executável | O repositório passaria a versionar geração de código, e código gerado que ninguém revisa roda contra dado de produção |
| Asserções absolutas sobre o dado (schema bate com o declarado, não há duplicata) | É outra pergunta — afirma sobre o dado, não sobre a mudança — e colide com `SF-DQ`, que a Fase 5c criou para julgar validação de dado dentro do job |
| Comparação linha a linha | Inviável sobre volume real, e é justamente por isso que a §3 declara os quatro como **proxies** |

## 3. A decisão que define o que a fase pode prometer

**Contagem, schema, chaves e agregados iguais não provam que o dado é o mesmo.**
Duas linhas podem trocar valores entre si e os quatro passam.

São proxies: fortes, baratos e incompletos. A fase afirma **"nenhum dos quatro
proxies detectou divergência"**, nunca "o resultado é idêntico". Isso vai escrito
na `explanation` de cada regra e na saída do comparador — não só neste spec.

É a mesma disciplina de `dq.unresolved` e de `bench.unresolved`: o que o motor
não sabe fica dito, e não vira silêncio que o leitor interpreta como aprovação.

## 4. Decisões de desenho

### D-1 — o plano é derivado, não perguntado

`funcval plan` monta o plano a partir dos facts que o motor já tem:
`pyspark.write` diz qual alvo o job escreve, `pyspark.join` dá as chaves,
`catalog.*` dá o schema declarado, `iceberg.*` e `s3.prefix_summary` dão o alvo
físico.

A alternativa recusada era só declarar o formato e deixar o operador escolher o
que validar. Ela produz validação que cobre o que alguém lembrou — que é
exatamente o defeito que `SF-DQ` mede em job real, e seria estranho o motor
acusar isso no código do usuário e cometer no próprio fluxo.

Cada item do plano cita o `fact_id` de onde saiu. Plano sem procedência seria
julgamento vestido de derivação.

### D-2 — o gate é satisfeito pelo plano, não pelo resultado

`functional_validation_defined` ganha `satisfied_by: funcval.plan`. Ver §1: o
nome do gate já dizia isso, e a ordem importa — definir depois de medir é escolher
o check que passa.

### D-3 — o comparador é módulo derivado, no padrão de `benchmark.py`

`sparkforge/facts/funcval.py`, função pura sobre `Fact`s: nunca executa, nunca lê
artefato bruto, nunca chama AWS. É o quarto módulo desta natureza
(`call_graph`, `fusion`, `benchmark`), e a forma está estabelecida e testada.

Isso também resolve, de novo, o limite que reaparece em toda fase:
`engine._condition_candidates` avalia um fact por vez, então "o depois divergiu
do antes" não é expressável como condição. O comparador decide e emite; o
catálogo lê atributo de um fact só.

### D-4 — tolerância só onde a aritmética a exige

Soma de ponto flutuante **depende da ordem de redução**: um `repartition`
legítimo muda a ordem e o total diverge nos últimos bits. Comparação exata
produziria falso positivo justamente nas mudanças que a fase existe para aprovar.

Comparação **exata** para inteiro, decimal, contagem e schema. **Tolerância
relativa** apenas para agregado de tipo de ponto flutuante, com o número no YAML
como `field-heuristic` declarada — não há fonte oficial que diga a partir de
quantos ULP uma diferença deixa de ser reassociação.

E a `explanation` diz o que a tolerância significa: divergência dentro dela **não
é prova de igualdade**, é ausência de prova de diferença.

### D-5 — cobertura é regra, não nota de rodapé

`SF-FVAL-005` dispara quando o resultado traz **menos** checks do que o plano
pediu. Validação parcial lida como aprovação é o encontro dos dois defeitos que
este projeto persegue: "nenhum problema" e "não coletei" ficando
indistinguíveis.

Sem essa regra, rodar metade do plano e passar seria o caminho de menor
resistência.

## 5. Facts

| Kind | Quando | Carrega |
|---|---|---|
| `funcval.plan` | `funcval plan` roda | os checks derivados, cada um com o `fact_id` de origem, o alvo e o tipo |
| `funcval.check_delta` | um check presente nos dois lados | valor antes, valor depois, e se divergiu — com a comparação usada (exata ou tolerância) |
| `funcval.analyzed` | sempre | sentinela: quantos checks o plano pediu, quantos vieram, quantos divergiram |
| `funcval.unresolved` | leitura impossível | check no plano e ausente no resultado; check no resultado e ausente no plano; valor não numérico onde a comparação exige número |

## 6. Regras

| Regra | Gatilho | Severidade |
|---|---|---|
| `SF-FVAL-001` | contagem divergiu | **P0** |
| `SF-FVAL-002` | schema divergiu — coluna ausente, tipo mudado | **P0** |
| `SF-FVAL-003` | chave duplicada depois, e não antes | P0 |
| `SF-FVAL-004` | agregado divergiu além da tolerância | P1 |
| `SF-FVAL-005` | cobertura: o resultado trouxe menos checks que o plano | P1 |

`runtime_scope: {}` nas cinco: o gatilho é comparação de valor, e não varia com
versão de Glue, Spark, EMR ou Iceberg.

## 7. Superfície

| Onde | O quê |
|---|---|
| `sparkforge/facts/funcval.py` | comparador; `EMITTED_KINDS` |
| `sparkforge/adapters/{_core,cli,tools}.py` | `funcval plan` e `funcval compare` |
| as duas listas `EXTRACTORS` | adições manuais independentes |
| as **quatro** listas de `tests/test_adapters_tools.py` | medidas na Fase 4b |
| `rules/catalog/funcval.yaml` | área `SF-FVAL` |
| `rules/catalog/routing.yaml` | `functional_validation_defined` ganha `satisfied_by` |
| `parity.yaml`, `manifest.json`, `scripts/regen_fixtures.py` | capacidade, tools, corpus |
| `agents/`, `skills/` | coordenador e fluxo |

## 8. Prova

`fixtures/funcval/`, com golden bidirecional: contagem divergindo, schema
divergindo, chave duplicada nova, agregado dentro e fora da tolerância, cobertura
parcial, e o caso limpo — os quatro proxies batendo e **nenhum achado**.

Mais a prova que fecha o par da §1: um case com `--strict-gates` **não** entra na
fase guardada sem `funcval.plan`, e entra com ele.

## 9. Critérios de sucesso

1. `funcval.py` não importa PySpark, não chama AWS, não lê artefato bruto
2. As cinco regras existem, com `runtime_scope: {}` e tolerância como `field-heuristic`
3. Toda regra tem golden positivo **e** negativo
4. Todo kind aparece em algum golden
5. `funcval plan` deriva de facts e cada check cita `fact_id`
6. `functional_validation_defined` ganha `satisfied_by: funcval.plan` e endurece
7. Comparação é exata para inteiro, decimal, contagem e schema; tolerante só para ponto flutuante
8. A saída do comparador declara que os quatro são **proxies**, não prova de igualdade
9. `SF-FVAL-005` dispara com resultado parcial, e há fixture
10. `SF-DQ` e `SF-FVAL` não acusam a mesma coisa — fronteira por construção, como a D-3 da Fase 5c

## 10. Riscos

| Risco | Mitigação |
|---|---|
| O leitor toma "quatro proxies bateram" por "o dado é idêntico" | §3, e o texto vai na saída e em cada `explanation`, não só aqui |
| A tolerância esconde divergência real | Só para ponto flutuante; exata no resto. E a `explanation` diz que dentro da tolerância não é prova de igualdade |
| O plano derivado cobre menos do que o operador precisaria | `SF-FVAL-005` cobra o que o plano pediu; o que o plano **não** pediu é limite declarado, e o operador pode acrescentar checks ao resultado — o comparador os reporta como não planejados em vez de ignorá-los |
| Fronteira com `SF-DQ` | Critério 10: `SF-DQ` julga validação **dentro do job**; `SF-FVAL` julga equivalência **entre duas execuções**. Nenhuma regra de uma lê fact da outra |

## 11. Desvios medidos na implementação

Este documento **não é reescrito** — o registro do que se pretendia numa data tem
valor próprio, e a convenção é a da seção "Como manter este arquivo honesto" do
[`STATUS.md`](../STATUS.md): spec obsoleto ganha seção de desvios e aponta para
lá, em vez de ser editado. O estado corrente é o [`STATUS.md`](../STATUS.md).

A implementação apurou **27** desvios numerados, `D-4c-1` a `D-4c-27`, cada um
com o texto medido na task que o encontrou —
[o plano](../plans/2026-08-04-sparkforge-fase4c-validacao-funcional.md) os carrega
por extenso, na seção *Desvios medidos* de cada task. Os seis abaixo são os que
tornam **este documento** errado onde ele afirma; os outros vinte e um são
medições que o plano registrou e que não contradizem nada escrito aqui.

**D-4c-1 — `pyspark.join` não dá as chaves, e dá menos do que a §4 supunha.** A
D-1 afirma que "`pyspark.join` dá as chaves". Não dá: o fact carrega
`measures.on_arity` — o **número** de colunas do `on` — e nunca os nomes. E há
menos que isso: `pyspark_ast.py:723-730` lê `node.args[1]`, então a forma com
keyword (`df.join(dim, on=["a","b"])`) não emite medida alguma. A varredura dos
102 kinds dos 16 extratores de então confirmou que **nenhum** fact nomeia chave de
negócio; os candidatos (`pyspark.dedup`, `pyspark.window`, `plan.join`,
`plan.exchange`, `sql.predicate`, `sql.projection`) carregam booleano, contagem
ou coluna de outra natureza. Contagem, schema e agregados seguem deriváveis, e os
agregados saem melhor do que a D-1 previa: `catalog.table_schema` dá coluna **e
tipo**, que é o que a D-4 precisa para escolher o modo de comparação.

**D-4c-2 — o eixo de chaves entra por declaração marcada, não por derivação.**
Consequência do D-4c-1. Sem `--key`, o plano não pede check de chave e **declara
o vazio**: `funcval.plan` carrega `undeclared_axes: ["keys"]` com a razão. Com
`funcval plan --key <col>[,<col>]`, o check entra com `origin: "declared"` e
`derived_from: []`; todo check derivado carrega `origin: "derived"` e o
`fact_id`. A D-1 continua valendo para os três eixos deriváveis; para o quarto, a
procedência passa a dizer **que é declarada** em vez de calar. Partição como
proxy foi medida e rejeitada: na fixture `catalog/glue_table_schema`, `db.eventos`
tem `distinct_values = partition_count = 1200` sobre `dt` para a tabela inteira —
um check de unicidade ali acusaria dado correto.

**D-4c-3 — o comparador nunca compara o resultado contra o catálogo.** O schema
declarado deriva **quais** colunas e tipos existem, e nada mais. A comparação é
sempre antes contra depois. Comparar o observado com o declarado é a asserção
absoluta que a §2 já pôs fora de escopo, e é pergunta de `SF-DQ` — o critério 10
da §9 depende disso valer também **dentro** do comparador, não só entre as áreas.

**D-4c-10 — o veredito da comparação relativa não é do módulo; é do catálogo, e a
§5 pedia as duas coisas ao mesmo tempo.** A §5 diz que o `check_delta` "diz se
divergiu", e a D-4 diz que o número que separa reassociação de divergência real é
`field-heuristic` sem fonte oficial. Para ponto flutuante as duas se excluem:
decidir exige o número, e o número mora no YAML. Some-se o contrato do próprio
dado — `Fact` é "observação determinística ancorada, **nunca contém juízo nem
limiar**" (`findings/models.py:32`) —, e um `diverged` de float seria um limiar
dentro de um Fact. Decisão: comparação **exata** continua decidindo `diverged` no
fact (que dois valores não sejam idênticos é observação, não limiar), e comparação
**relativa** sai com `measures.relative_delta` e **sem** `diverged`, com
`attrs.diverged_omitted_reason` dizendo por quê. Quem julga é a `SF-FVAL-004`,
contra `threshold.relative_tolerance`. Consequência para a sentinela:
`relative_delta_check_count` existe para que `diverged_check_count == 0` não seja
lido como "nada divergiu" quando significa "ninguém aqui decidiu".

**D-4c-23 — a `SF-FVAL-004` precisa de DUAS condições, e a §6 descreve uma.** Um
`agg:sum:<coluna>` de coluna **inteira** ou **decimal** é comparado de forma exata
e sai **com** `diverged`. Uma 004 escrita só sobre `relative_delta` deixaria essa
divergência aparecer em `diverged_check_count` e em achado **nenhum**: silêncio
com cara de aprovação. A regra ficou com `when.any` de duas condições — a exata
lendo `attrs.diverged`, a relativa lendo `measures.relative_delta` contra o limiar.

O buraco é de DUAS naturezas, e a segunda é a que decide. **Por magnitude:** uma
soma que muda em uma unidade só escapa do limiar `1.0e-9` quando o total passa de
**um bilhão** — medido pelo `judge`, o corte fica em ~9,95e8, e abaixo dele a via
relativa ainda pegaria (sobre quinhentos milhões o `relative_delta` é `2e-9`, que
é **acima** do limiar, não abaixo). **Por forma, e esta não tem magnitude:** a
condição relativa é filtrada por `attrs.comparison: relative`, e um agregado exato
nunca casa com ela — medido, a 004 sem a condição exata fica muda para um `bigint`
divergente em **qualquer** ordem de grandeza, inclusive uma soma de mil.

**D-4c-25 — o gate morde em `report`, e não em `validation`.** A §7 não fixava a
fase. Guardar `validation` mataria a `ROUTE-015`, única rota com
`blocked_by: [functional_validation_defined]`: o `when` dela é o gate **falso**, e
um case sob rigor não entraria em `validation` com o gate falso — a única rota que
manda definir a validação nunca apareceria. Guardando só `report`, o case entra em
`validation`, a rota casa ali, o operador roda `funcval plan`, e o fechamento
passa a exigir o plano.

### Um desvio a mais, medido ao fechar a fase

**D-4c-26 — `funcval compare` não tem `--out`, e a §7 não previu a assimetria.**
`funcval plan` grava o artefato (`--out` obrigatório, porque ele é a entrada do
`compare` e a evidência do gate); `compare` **imprime** o envelope paginado e não
escreve arquivo nenhum. Consequência prática, medida na CLI: para julgar os
`funcval.check_delta` é preciso redirecionar a saída e extrair `items` — que é o
formato que `judge --facts` espera —, e conferir `next_cursor`, porque `--limit`
vale 50 por default e um plano grande pagina. Está registrado como **dívida** no
`STATUS.md`, não como limite: fechá-la é escrever `--out`/`out_path` nos dois
adaptadores, sem reverter decisão nenhuma. O contorno está escrito onde o verbo
é ensinado, que é **uma** skill e não duas: `benchmark-pyspark-job` ensina
`funcval compare` e carrega a extração de `items` e a conferência de
`next_cursor`; `review-pyspark-pr` ensina só `funcval plan` — que **tem**
`--out` — e delega a comparação à outra skill, então não há contorno a carregar.
