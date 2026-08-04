# SparkForge AWS — Fase 4a: benchmark antes/depois, derivado de dois event logs

**Data:** 2026-08-03
**Status:** desenhado, não implementado.
**Fecha:** o primeiro dos quatro itens da Fase 4 do roadmap (§16 do
[spec da Fase 0](2026-07-29-sparkforge-fase0-design.md)) — *rigor*.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: um gate que existe e não tem produtor

`validate_finding` rejeita achado que afirma ganho sem `benchmark_ref`. A regra
está no motor desde a Fase 0, é testada, e **nada no repositório produz um
`benchmark_ref`**. O campo é uma string que o agente preenche por conta própria,
ou não preenche e perde o achado.

É a mesma classe de defeito que `SF-EMR-009` fechou na Fase 5b — mecanismo
existindo sem garantia declarada — com uma diferença que a torna pior: aqui o
mecanismo é um **gate**. Um gate sem produtor tem dois desfechos, e os dois são
ruins: ou o operador aprende a preencher o campo com qualquer coisa para o
achado passar, e o gate vira obstáculo a contornar; ou os achados de ganho
somem, e o motor fica mudo justamente sobre o que ele existe para provar.

O projeto acumulou cinco áreas de regra em três dias. O que sustenta cada achado
hoje é `fact_id` mais golden bidirecional — determinismo. O que **não** existe é
prova de que a recomendação funcionou.

## 2. Objetivo

Uma área `SF-BENCH` que afirma sobre a **comparação entre duas execuções**, a
partir dos event logs que o motor já sabe ler, e um `benchmark_ref` que cita
`fact_id` em vez de texto livre.

**Critério de sucesso central:** um par de event logs — antes e depois de uma
mudança — produz achado citando `fact_id`, e um achado que afirma ganho só passa
por `validate_finding` quando o `benchmark_ref` aponta para um `bench.run_delta`
que existe no mesmo conjunto de facts.

### Não-objetivos, com razão registrada

| Fora de escopo | Razão |
|---|---|
| **Executar Spark** — submeter o job, medir sozinho | Quebraria a propriedade central: mesma entrada, mesma saída. Passaria a exigir cluster, credencial, dado de teste e orçamento, e faria a suíte depender de infraestrutura. O motor lê artefato; quem executa é o operador, no ambiente dele |
| Validação funcional (contagem, schema, chaves, agregados) | Exige artefato que não existe — resultado de consultas que alguém precisa rodar. Mecanismo diferente do desta fase, que não precisa de artefato novo nenhum. Fase 4b |
| Gates fail-closed e assinatura de relatório | Dependem de haver evidência para gatear e relatório para assinar. Fase 4b |
| Comparar mais de duas execuções | Uma série temporal é outro problema, com outra pergunta (tendência, não delta). Nada nesta fase impede uma fase futura de fazê-lo |

## 3. Decisões de desenho

### D-1 — o motor não executa; ele deriva

Nenhum código novo submete job, chama AWS ou importa PySpark. A entrada são
`Fact`s já extraídos por `analyze event-log`, que existe desde a Fase 1 e tem
golden próprio.

### D-2 — módulo derivado, no padrão de `call_graph.py`

`sparkforge/facts/benchmark.py`, com `build_benchmark(before, after, path_hint="")`
— função pura sobre `Fact`s, que nunca reparseia artefato. É o terceiro módulo
desta natureza (`call_graph.py` deriva do AST, `fusion.py` correlaciona entre
extratores), e a forma já está estabelecida e testada.

Isso também resolve, sem alargar o motor, o problema que reaparece em toda fase:
`engine._condition_candidates` avalia **um fact por vez**, então "o run depois é
pior que o antes" não é expressável como condição de regra. O comparador decide e
emite; o catálogo lê atributo de um fact só. Mesmo padrão de `SF-EMR-008` e de
toda a Fase 5c.

### D-3 — casamento de stage é estrito, e o que não casa é contado

O subject de stage é `{"type": "stage", "symbol": "...", "stage_id": N}`. O
`stage_id` **não** é estável entre execuções, e o `symbol` — derivado do código —
muda exatamente quando a mudança foi significativa. Um benchmark existe porque o
código mudou; casar stage é confiável só no caso menos interessante.

Portanto: `bench.run_delta` (totais da execução) é afirmado **sempre**, porque
totais são comparáveis mesmo com o código mudando. `bench.stage_delta` sai
**apenas** quando o `symbol` é idêntico nos dois runs. Nada de casar por posição,
por `stage_id` ou por similaridade de nome — e o que não casou vira
`bench.unmatched` mais um contador em `bench.analyzed`, nunca omissão. É a
disciplina de `opaque_caller_function_count` da Fase 5b.

### D-4 — `SF-BENCH-001` não suprime as outras três

Se os volumes de entrada divergem, a comparação não sustenta conclusão — e é
tentador fazer as outras regras calarem. **Não calam.** Elas afirmam sobre o que
foi medido, e o P0 de `SF-BENCH-001` aparece no mesmo relatório dizendo que a
medição não sustenta conclusão. Suprimir criaria acoplamento entre regras da
mesma área, que é o que a Fase 5a passou uma fase inteira desfazendo, e o
operador que lê `002` sem ver `001` teria sido enganado pela supressão tanto
quanto pela ausência.

### D-5 — `benchmark_ref` passa a citar `fact_id`

`validate_finding` já exige o campo para achado que afirma ganho. Passa a exigir
que o valor seja o `fact_id` de um `bench.run_delta` **presente no conjunto de
facts do próprio achado**. Texto livre deixa de passar.

É a linha que transforma esta fase de "mais uma área" em "o gate de ganho passou
a ter produtor", e é ela que fecha a §1.

### D-6 — sem coordenador novo

A área se pendura em `spark-performance-architect`, que já existe e já declara a
skill `benchmark-pyspark-job`. Ao contrário da Fase 5c — onde `SF-DQ` ganhou
coordenador próprio porque a pergunta era outra —, aqui a pergunta é a mesma que
aquele coordenador já responde: *o job ficou mais rápido, e por quê*. Coordenador
novo seria porta separada para a mesma sala.

`tests/test_agent_coverage.py::test_no_area_is_orphan` fica satisfeito por
`rule_areas`, e a skill existente ganha a seção do fluxo novo.

## 4. Facts

### 4.1 Kinds emitidos

| Kind | Quando | Carrega |
|---|---|---|
| `bench.run_delta` | sempre que os dois lados têm `spark.log_analyzed` | por medida (duração somada, input, spill, GC, pico de memória, contagem de tasks): valor antes, valor depois, delta relativo |
| `bench.stage_delta` | `symbol` de stage idêntico nos dois runs | as mesmas medidas, no recorte daquele stage |
| `bench.unmatched` | stage presente num run e ausente no outro | o `symbol` e de que lado ele estava |
| `bench.analyzed` | sempre | sentinela: quantos stages casaram, quantos não, e os dois artefatos de origem |
| `bench.unresolved` | leitura impossível | motivo: um dos lados sem `spark.log_analyzed`, medida ausente dos dois lados |

**Delta relativo, não absoluto,** é o que a regra lê: "300 s a menos" não diz nada
sem saber de quanto para quanto. O valor absoluto dos dois lados vai junto, para
o operador conferir sem refazer a conta.

### 4.2 Regras

| Regra | Gatilho | O que ela impede |
|---|---|---|
| `SF-BENCH-001` | `bench.run_delta` com input dos dois runs divergindo além do limiar | A mentira clássica: comparar execuções sobre volumes diferentes. Sem ela, as outras três herdam a mentira. **P0** |
| `SF-BENCH-002` | duração relativa piorou além do limiar | Regressão: a mudança custou tempo |
| `SF-BENCH-003` | duração melhorou **e** spill ou pico de memória subiu | Ganho frágil — rápido no volume medido, e o próximo lote maior derruba |
| `SF-BENCH-004` | `bench.analyzed` com taxa de stage não casado acima do limiar | Delta por stage não é interpretável, e dizer isso é melhor que deixar `stage_delta` parcial passar por quadro completo |

`runtime_scope: {}` nas quatro: o gatilho é comparação de medida, e não varia com
versão de Glue, Spark, EMR ou Iceberg. Critério fixado na Fase 5a.

**Todos os limiares são `field-heuristic` declarada.** Não há fonte oficial que
diga a partir de quantos por cento uma divergência de volume invalida uma
comparação, e inventar citação seria pior que assumir o julgamento. Onde a medida
permitir, `severity_by` sobre ela em vez de limiar único.

## 5. Superfície e registro

Onze pontos, medidos na Fase 5c e conferidos aqui:

| Onde | O quê |
|---|---|
| `sparkforge/facts/benchmark.py` | `EMITTED_KINDS` |
| `tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py` | `EXTRACTORS` — **duas listas manuais independentes** |
| `sparkforge/adapters/cli.py`, `_core.py` | verbo `benchmark --before <facts> --after <facts>` |
| `sparkforge/adapters/tools.py` | `sparkforge_benchmark` (spec, handler, dict) |
| `tests/test_adapters_tools.py` | as **três** listas manuais que a Fase 5c descobriu |
| `parity.yaml`, `manifest.json` | capacidade e tool declaradas |
| `scripts/regen_fixtures.py` | `regen_bench` + a constante + o par na lista |
| `rules/catalog/benchmark.yaml` | a área |
| `agents/spark-performance-architect.md` | `SF-BENCH` em `rule_areas` |
| `skills/benchmark-pyspark-job/SKILL.md` | o fluxo novo, com runtime em toda invocação de `judge` |
| `sparkforge/findings/validate.py` | `benchmark_ref` citando `fact_id` |

**Sem verbo `collect`:** os event logs já são coletados por `collect event-log`.

## 6. Prova

`fixtures/bench/`, com golden bidirecional. Cada fixture é um **par** de dumps de
event log em `input/`, e o `meta.yaml` diz qual é o antes e qual é o depois:

| Fixture | Prova |
|---|---|
| `regression_slower` | positivo de `SF-BENCH-002` |
| `different_input_volume` | positivo de `SF-BENCH-001` — e negativo de nada: as outras continuam avaliando (D-4) |
| `faster_but_spilling` | positivo de `SF-BENCH-003` |
| `most_stages_renamed` | positivo de `SF-BENCH-004`, com `bench.unmatched` e o contador |
| `clean_improvement` | negativo das quatro: mais rápido, mesmo volume, sem spill novo, stages casando |
| `one_side_missing` | `bench.unresolved` — um lado sem `spark.log_analyzed` |

Mais a prova de ponta a ponta: um achado que afirma ganho **passa** por
`validate_finding` quando cita o `fact_id` do `bench.run_delta`, e **falha**
quando cita texto livre ou um `fact_id` ausente do conjunto.

## 7. Critérios de sucesso

1. `benchmark.py` emite os cinco kinds, com `EMITTED_KINDS` declarado, sem importar PySpark nem chamar AWS
2. As quatro regras existem, com `runtime_scope: {}` e limiares como `field-heuristic` declarada
3. Toda regra tem golden positivo **e** negativo
4. Todo kind aparece em algum golden
5. `SF-BENCH` tem coordenador (`spark-performance-architect`) e `test_no_area_is_orphan` passa sem exceção
6. Verbo CLI e tool MCP existem, e `parity.yaml` declara a capacidade nas cinco plataformas
7. `benchmark_ref` com texto livre é **rejeitado**; com `fact_id` de `bench.run_delta` presente, aceito — com teste dos dois lados
8. `SF-BENCH-001` disparando **não** impede `002`, `003` e `004` de avaliar, e há fixture que prova
9. Stage casado por acidente é impossível: casamento por `symbol` idêntico, e o não casado contado

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Limiar de divergência de volume acusa comparação legítima | `field-heuristic` declarada com o número no YAML, `severity_by` sobre a medida, e a fixture `clean_improvement` fixando o lado negativo |
| Operador passa antes e depois trocados | `bench.analyzed` nomeia os dois artefatos de origem, e o delta relativo tem sinal — inversão aparece como regressão implausível, não como silêncio |
| `benchmark_ref` estrito quebra achados que hoje passam | É o objetivo, e é mudança de contrato. Precisa aparecer no `STATUS.md` como quebra declarada, não como detalhe |
| Event log de Glue e de EMR diferirem no que preenchem | O comparador lê `Fact`s já normalizados por `event_log.py`; medida ausente de um lado vira `bench.unresolved`, nunca zero |

## 9. Desvios apurados na implementação

Este documento **não é reescrito** — o registro do que se pretendia numa data tem
valor próprio, e a convenção do repositório é a da seção "Como manter este
arquivo honesto" do [`STATUS.md`](../STATUS.md): spec obsoleto ganha seção de
desvios e aponta para lá, em vez de ser editado. O estado corrente é o
[`STATUS.md`](../STATUS.md); os desvios que a implementação apurou ficam aqui.

**D-4a-A — a medida do `bench.run_delta` não é duração, é tempo de task somado.**
Três lugares deste documento a chamam de *duração* — a linha da tabela §4.1, e as
linhas de `SF-BENCH-002` e `SF-BENCH-003` na tabela §4.2. É o único documento do
repositório que faz isso; o catálogo, o `STATUS.md` e o plano dizem **tempo de
task**. O nome da chave é `total_task_ms`, e ela é a soma de `mean_ms *
task_count` sobre os stages — **trabalho**, não tempo de relógio. Não existe fact
de duração de relógio no event log lido: `facts/event_log.py` emite duração por
stage e nada de wall-clock.

A diferença não é vocabular. Um job pode terminar **antes** no relógio somando
**mais** tempo de task, se a mudança passou a paralelizar melhor, e o inverso
também acontece. Por isso `SF-BENCH-002` acusa "mais trabalho" e nunca "mais
lento", e a `explanation` dela manda confirmar no relógio antes de reverter a
mudança — é a regra que lê a medida que manda alguém desfazer trabalho. Chamá-la
de duração teria sido o defeito que a Fase 5b corrigiu em
`unreachable_function_count`: nome que promete mais do que entrega. O cabeçalho
de `rules/catalog/benchmark.yaml` registra a decisão por extenso.

**D-4a-B — `bench.run_delta` não compara pico de memória.** A linha §4.1 lista
"pico de memória" entre as medidas que o fato carrega, e `_RUN_MEASURES`
(`sparkforge/facts/benchmark.py`) tem cinco medidas, nenhuma delas essa:
`total_task_ms`, `total_input_bytes`, `total_spill_bytes`, `total_gc_ms` e
`total_task_count`. A linha de `SF-BENCH-003` na §4.2 herda o erro ao dizer
"spill **ou pico de memória** subiu"; o gatilho implementado é spill **ou GC**.

O que existe é o fact `spark.executor.memory_usage`, emitido por
`facts/event_log.py` a partir de `SparkListenerStageExecutorMetrics` — **um fact
por executor**, e é aí que a comparação não fecha. As cinco medidas do run são
somas sobre stages; pico de memória não soma, e o pico de um executor não casa
com o de outro entre duas execuções, porque `Executor ID` não é estável. Comparar
o máximo dos dois lados esconderia justamente o caso que aquele fact existe para
mostrar: um executor no limite entre dez folgados. A medida continua disponível
ao operador no fact de cada lado, e a `validation` da `SF-BENCH-003` a cita
nominalmente — o que ela não é, é gatilho.
