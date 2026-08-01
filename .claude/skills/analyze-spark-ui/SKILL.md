---
name: analyze-spark-ui
description: Use quando houver um Spark event log, um job run id ou um Spark UI aberto de um job AWS Glue e for preciso achar stage dominante, skew de task, spill, GC, executor perdido ou subparalelismo. Use também quando a pergunta for "por que este stage demora", "por que uma task não termina", "o executor sumiu" ou "está com spill", mesmo que ninguém fale em event log. Se você está prestes a ler métrica de execução de Spark no olho, rode `sparkforge collect event-log` e `sparkforge analyze event-log` em vez disso — o extrator calcula p50/p95/max, spill e GC por stage, e o catálogo aplica os limiares versionados.
---

# Analyze Spark UI

Ler Spark UI no olho não escala e não é reproduzível: dois analistas olhando o mesmo stage discordam sobre se `max/p50 = 2.8` importa. O extrator resolve isso — ele calcula as distribuições, e o catálogo aplica limiares versionados com fonte datada.

Seu trabalho não é calcular. É **coletar, rodar, e interpretar o que voltou**.

## Procedimento

### 1. Garanta o event log

```bash
sparkforge collect event-log --job-run <id> --bucket <bucket> --prefix <prefix> --now <ISO8601>
```

Sem credencial AWS, baixe o log manualmente para `.sparkforge/artifacts/eventlog/<id>.jsonl` e registre com `sparkforge.collect.register_artifact` — o manifesto é o que permite retomar em outra máquina.

Se o job não tem `--enable-spark-ui` e `--spark-event-logs-path`, não há log e não vai haver. Esse é o achado: `SF-GLUE-002`, observabilidade ausente. Reporte e pare — nenhuma métrica de execução existe para analisar.

### 2. Extraia os facts

```bash
sparkforge analyze event-log --path .sparkforge/artifacts/eventlog/<id>.jsonl --out .sparkforge/facts.json
```

Leia `unresolved` na saída. Linha malformada ou log truncado vira `spark.unresolved`, e isso é ponto cego, não ausência de problema. Reporte a contagem sempre.

### 3. Julgue

```bash
sparkforge judge --facts .sparkforge/facts.json --show-skipped
```

`--show-skipped` não é opcional. Ele diz quais regras **não** foram avaliadas e por quê — sem isso você não distingue "nenhum problema" de "não coletei o dado que provaria o problema".

A flag de versão também não é: o event log declara o runtime na própria primeira linha (`SparkListenerLogStart`), o extrator emite isso como `spark.runtime_version`, e `judge` usa como fonte. Leia o campo `runtime` da saída para ver o que ele usou, com `detected_from: ["event_log"]`.

**Mas o event log preenche `spark`, não `glue`.** A derivação é de mão única — sabendo a versão do Glue sai a do Spark pela matriz de compatibilidade, e não o contrário, porque uma mesma versão de Spark aparece em mais de uma versão de Glue. Consequência prática: as seis regras `SF-GLUE-*` continuam puladas com `reason: runtime_scope` mesmo com o log inteiro em mãos. Nenhuma regra `SF-UI-*` guarda versão, então a análise desta skill não perde nada — mas se `--show-skipped` mostrar `SF-GLUE-002` (observabilidade) e você quiser cobrir esse eixo, junte os facts do Terraform na mesma chamada (`--facts` é repetível) em vez de digitar a versão:

```bash
sparkforge analyze terraform --path <dir.tf> --out .sparkforge/facts_tf.json
sparkforge judge --facts .sparkforge/facts.json --facts .sparkforge/facts_tf.json --show-skipped
```

Se o log e o `.tf` discordarem sobre a versão do Spark, `runtime.divergences` mostra os dois valores — e essa é a leitura mais valiosa desta saída, porque um job rodando em runtime diferente do declarado invalida todo limiar versionado aplicado depois.

### 4. Interprete

Aqui começa seu trabalho de verdade. As regras dizem o que disparou; você diz o que fazer.

## O que cada fact significa

| Fact | O que mede | Por que importa |
|---|---|---|
| `spark.stage.task_duration` | p50, p95, max por stage | O stage termina quando a última task termina. Uma task muito acima da mediana é cluster ocioso esperando por ela |
| `spark.stage.task_input` | mesma distribuição, em bytes lidos | **É o discriminador.** Duração desigual com input uniforme é skew de computação, e repartition não resolve |
| `spark.stage.spill` | spill de memória e disco vs. input | Spill maior que o input significa algoritmo ou tamanho de partição inadequados, não só falta de memória |
| `spark.stage.gc` | GC time vs. executor run time | GC alto com heap **não** cheio indica objetos de vida curta, típico de UDF Python. Com heap cheio é dado demais por executor. Correções opostas |
| `spark.executor.lost` | remoção, com `heap_oom_in_log` | Executor removido **sem** OOM de heap no log é estouro de container fora do heap. A correção é `memoryOverhead`, não `memory`. "Aumentei a memória e continuou" é a assinatura de ter classificado errado |
| `spark.stage.task_count` | tasks vs. cores disponíveis | Cores pagos e ociosos. Causa comum: arquivo de texto gzip, que é sempre uma task só |

## A pergunta que decide o tratamento

Quando `SF-UI-001` (skew de duração) dispara, olhe imediatamente se `SF-UI-002` (skew de input) também disparou:

- **Os dois juntos** → skew de dados. Tratável na chave: nulls, hot key, valor sentinela.
- **Só o de duração** → skew de computação. UDF caro em certas linhas, `explode` desigual. Repartition não muda nada, e tentar isso é o erro mais caro dessa análise.

`ROUTE-006` e `ROUTE-007` em `rules/catalog/routing.yaml` já codificam essa bifurcação. `sparkforge next-step` a aplica sozinho.

## Referência rápida

Regras desta área, e o fact que cada uma consome. Os limiares **não** estão aqui de propósito: eles mudam quando aparece evidência nova, e um número decorado vira mentira silenciosa quando o catálogo é atualizado. Consulte com `sparkforge rules lookup --id <ID>`, que devolve limiar, guarda de versão, risco, validação, rollback e fonte com data.

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-UI-001` | `spark.stage.task_duration` | Duração desigual entre tasks do mesmo stage |
| `SF-UI-002` | `spark.stage.task_input` | Bytes lidos desiguais — discrimina skew de dados de skew de computação |
| `SF-UI-003` | `spark.stage.spill` | Spill desproporcional ao input |
| `SF-UI-004` | `spark.stage.gc` | GC consumindo fração alta do tempo de executor |
| `SF-UI-005` | `spark.executor.lost` | Executor removido, com ou sem OOM de heap no log |
| `SF-UI-006` | `spark.stage.task_count` | Tasks abaixo dos cores disponíveis |

## Quando NÃO usar

- Só tem o plano físico, sem métricas de execução → `analyze-spark-plan`
- Skew já confirmado e quer tratar → `diagnose-data-skew`
- Executor perdido é o sintoma dominante → `diagnose-oom`
- Quer provar que uma mudança melhorou → `benchmark-pyspark-job`

## Red flags

- **Tratar a task mais lenta como o job todo.** Olhe a distribuição, não o máximo isolado.
- **Confundir espera de I/O com falta de CPU.** CPU baixa com listing alto é layout de arquivos, e mais worker não corrige.
- **Ignorar executor removido.** Pode ser OOM de container silencioso, que não aparece como OOM no log.
- **Recomendar mais worker antes de descartar skew, small files e trabalho no driver.** Em `knowledge/glue/workers-and-capacity.md`, quatro das oito linhas da tabela de decisão têm capacidade como resposta errada.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
