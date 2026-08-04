# SparkForge AWS — Fase 4c: validação funcional automatizada

**Data:** 2026-08-04
**Status:** desenhado, não implementado.
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
