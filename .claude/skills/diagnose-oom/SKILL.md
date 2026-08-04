---
name: diagnose-oom
description: Use quando um job Glue falha com OutOfMemory, "Container killed by YARN", "GC overhead limit exceeded", ExecutorLostFailure, estouro de Python worker/pandas_udf, ou frases como "o job morreu depois de 3 horas" e "aumentei a memória e continuou". Use para classificar se é heap de driver, heap de executor, overhead de container, broadcast, metadata/plan explosion ou Python worker antes de mitigar. Se você está prestes a estimar heap e GC no olho, rode `sparkforge collect event-log`, `sparkforge analyze event-log` e `sparkforge judge` em vez disso — o fact `spark.executor.lost` já vem com `heap_oom_in_log`: executor removido sem OOM de heap no log é estouro de container fora do heap (a correção é `memoryOverhead`, não `memory`), e é o OOM mais mal diagnosticado que existe.
---

# Diagnose OOM

"O job deu OOM" não é diagnóstico. `knowledge/spark/memory-and-oom.md` seção 2 lista sete classes com causas e correções diferentes, e classificar errado leva a aumentar worker quando o problema é um plano, ou a mexer no código quando o problema é disco. Dois discriminadores do toolkit resolvem as classes mais comuns sem chute.

## Procedimento

1. `sparkforge collect event-log --repo . --job-run <id> --bucket <bucket> --prefix <prefix> --now <ISO8601>`.
2. `sparkforge analyze event-log --path .sparkforge/artifacts/eventlog/<id>.jsonl --out .sparkforge/facts.json`. Reporte `unresolved` sempre — log truncado no meio da falha é o caso mais comum aqui, e é ponto cego, não ausência de causa.
3. `sparkforge collect cloudwatch --repo . --job-name <nome> --job-run <id> --start <ISO8601> --end <ISO8601> --now <ISO8601>`. **Não há extrator de facts para CloudWatch ainda** — isto baixa o artefato bruto, e você lê `glue.driver.memory.heap.used.percentage`, `glue.ALL.memory.heap.used.percentage`, `glue.ALL.memory.non-heap.used.percentage` e `glue.ALL.disk.used.percentage` manualmente, como série temporal, conforme `knowledge/spark/memory-and-oom.md` seção 6. Diga isso no relatório em vez de fingir que veio de um julgamento automático.
4. `sparkforge judge --facts .sparkforge/facts.json --show-skipped` aplica `SF-UI-004` (GC) e `SF-UI-005` (executor perdido). Nenhuma das duas guarda versão, então a flag não muda a classificação do OOM — omita e leia o campo `runtime` da saída, que mostra o que `judge` inferiu: o event log declara a versão do Spark na primeira linha e vira `spark.runtime_version`, com `detected_from: ["event_log"]`. Isso preenche `spark`, **não** `glue` (a matriz de compatibilidade deriva numa direção só), então `SF-GLUE-*` continua em `--show-skipped` com `reason: runtime_scope`. Para esta skill isso é aceitável: a classificação heap-vs-container sai de `attrs.heap_oom_in_log`, não de versão. Mas a *recomendação* que vem depois é uma mudança de configuração de memória, e o protocolo exige runtime confirmado antes disso — se for propor um valor de `memoryOverhead` ou de worker type, junte os facts do Terraform na mesma chamada (`--facts` é repetível) para que `runtime.glue` deixe de ser vazio, ou declare com `--glue` a versão que você conhece de fonte confiável.
5. `sparkforge next-step --repo . --findings .sparkforge/findings.json` roteia para cá automaticamente quando `SF-UI-005` dispara (`ROUTE-005`).

## O discriminador que decide tudo: `heap_oom_in_log`

O extrator de event log classifica cada `SparkListenerExecutorRemoved` procurando assinaturas de OOM de heap JVM (`java.lang.OutOfMemoryError`, `GC overhead limit`, `Java heap space`) no texto de `Removed Reason`, e grava o resultado em `attrs.heap_oom_in_log` do fact `spark.executor.lost`.

- **Presente** → OOM de heap real. `spark.executor.memory` é o eixo certo.
- **Ausente**, com o executor removido do mesmo jeito → estouro de memória do *container*, fora do heap: worker Python, buffers Arrow, buffers de rede, metaspace. A correção é `spark.executor.memoryOverhead`, **não** `spark.executor.memory`. `SF-UI-005` dispara justamente nesse caso (`heap_oom_in_log: false`), com severidade `P0`.

"Aumentei a memória e continuou" é a assinatura de ter classificado este caso como heap quando era container. Se você está prestes a recomendar subir `spark.executor.memory`, confirme `heap_oom_in_log` primeiro.

## GC: heap cheio ou objetos de vida curta

`SF-UI-004` compara `gc_ms` contra `executor_run_ms` do stage. As duas causas têm correções opostas, e por isso é obrigatório cruzar com a série temporal de `glue.ALL.memory.heap.used.percentage` (do CloudWatch bruto do passo 3) antes de decidir:

- GC alto **com heap não cheio** → muitos objetos de vida curta, típico de UDF Python ou conversão linha a linha. Eliminar a UDF, não aumentar memória.
- GC alto **com heap cheio** → dado demais por executor. Reduzir dado por task ou usar worker com mais memória.

## Classes que o event log não cobre sozinho

Nem toda classe de OOM aparece em `spark.executor.lost` ou `spark.stage.gc`. Cruze com os facts estáticos de `sparkforge analyze pyspark`:

- **Driver OOM** (`collect`/`toPandas` sem limite) → finding `SF-PY-002` sobre `pyspark.driver_collect`.
- **Broadcast OOM** (hint de broadcast num lado que cresceu) → finding `SF-PY-009` sobre `pyspark.join`.
- **Metadata/plan explosion** (sequência longa de `withColumn`, muitos manifests Iceberg) → finding `SF-PY-007` sobre `pyspark.withcolumn_run`, ou `optimize-iceberg-table` para dívida de metadados.
- **Python worker** (`pandas_udf` com batch grande, `MemoryError` no log Python) → finding `SF-PY-001` sobre `pyspark.udf`.

O texto completo da exceção ainda precisa ser lido — nenhum extrator classifica a mensagem em si além do heap; a taxonomia completa das sete classes está em `knowledge/spark/memory-and-oom.md` seção 2.

## Referência rápida

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-UI-004` | `spark.stage.gc` | GC consumindo fração alta do tempo de executor — cruzar com heap para separar as duas causas opostas |
| `SF-UI-005` | `spark.executor.lost` (`attrs.heap_oom_in_log`) | Executor removido, com ou sem OOM de heap no log — o discriminador container-vs-heap |

Limiares e severidade vêm de `sparkforge rules lookup --id <ID>`, nunca de memória.

## Quando NÃO usar

- Não há falha, só lentidão ou custo: use `analyze-spark-ui` ou `tune-glue-job`.
- O OOM ocorre dentro de um loop de batches: combine com `analyze-batch-loop` — acúmulo por iteração é a causa mais comum de OOM "depois de horas".
- A causa é uma chave quente confirmada, sem sinal de memória: aprofunde em `diagnose-data-skew`.

## Red flags

- Aumentar `spark.executor.memory` quando `heap_oom_in_log` é `false` — o eixo certo é `memoryOverhead`.
- Tratar "aumentei a memória e continuou" como "preciso de mais memória ainda" em vez de reclassificar a causa.
- Não registrar em qual iteração/batch a falha ocorre em jobs com loop — sem isso, `analyze-batch-loop` não tem por onde começar.
- Aumentar worker type/memória como primeira e única resposta, antes de confirmar heap vs. container.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva você **não executa** — recomende, e a confirmação de escopo e
retenção **sobe a quem pode ser perguntado**: o agente pai que despachou, ou o
operador na sessão.

Esta skill é **despachável** (`subagent: true` no espelho `.agents/skills/`), e
`ask_user_question` é **sempre negado** a um subagente. Dentro do despacho, obter a
confirmação aqui não é difícil: é impossível — por isso a regra 9 de
`AGENT_PROTOCOL.md` manda não executar e devolver a decisão a quem pode ser
perguntado.
