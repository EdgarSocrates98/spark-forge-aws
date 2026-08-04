---
name: analyze-spark-plan
description: Use quando tiver a saída de df.explain (formatted/extended/cost) ou EXPLAIN e precisar interpretar scans, PartitionFilters/PushedFilters, Exchange/shuffle, estratégia de join (BroadcastHashJoin, SortMergeJoin, ShuffledHashJoin, BroadcastNestedLoopJoin, CartesianProduct), Sort, Window, HashAggregate, Generate/explode, UDF Python no plano (BatchEvalPython/ArrowEvalPython) e o antes/depois do AQE. Use também quando a pergunta for "por que não usa broadcast", "por que lê a tabela inteira", "o filtro não desceu pro scan" ou "quantos shuffles esse job tem", mesmo sem citar explain. Salve o `explain` num arquivo e rode `sparkforge analyze plan`: ele emite `plan.file_scan`, `plan.join`, `plan.python_udf`, `plan.aqe` e `plan.exchange`, julgados por `SF-PLAN-001..004`, `SF-PQ-002` e `SF-PQ-004`. Para concluir causa (skew, spill, OOM), junte `analyze pyspark` e o `analyze event-log` da execução: o plano diz o que foi declarado, não o que custou.
subagent: true
---

# Analyze Spark Plan

`sparkforge analyze plan` lê a saída de `explain()` e a transforma em facts. O que ele **não** faz é inventar o que o texto não diz: `explain()` é saída para humano, não formato de máquina, e o extrator declara o ponto cego em vez de meio-parsear. Três limites valem antes de qualquer conclusão:

- **Modo.** `formatted` é o preferido (um campo por linha, sem ambiguidade de vírgula); `simple` e `extended` são suportados — de `extended`/`cost` só a seção `== Physical Plan ==` é interpretada, e as seções lógicas são ignoradas de propósito, contadas em `measures.skipped_logical_lines`, nunca em `unresolved`. `codegen` é **rejeitado**: é Java gerado, não plano, e vira `plan.unresolved` com `reason: unsupported_mode`.
- **Truncamento.** O Spark corta listas longas de campos com `... 56 more fields`. Contar o que sobrou inflaria em silêncio a razão de `SF-PQ-004`, então o extrator não emite `read_schema_columns` nem `referenced_columns` nesse caso: emite `plan.unresolved` com `reason: truncated_field_list`, e a regra não dispara. **Não leia isso como "sem achado"** — leia como "não deu para contar".
- **Plano declarado ≠ plano executado.** O plano não revela distribuição real de dados, spill, GC, nem a estratégia de join que o AQE efetivamente escolheu em runtime. `SF-PLAN-004` existe justamente para marcar o plano como não-final quando o AQE está ligado.

O checklist de leitura em `knowledge/spark/plan-reading.md` continua sendo o trabalho de domínio — o extrator ancora e o `judge` julga, mas quem interpreta a árvore é você.

## Procedimento

1. **Obtenha o plano físico e salve em arquivo.** `df.explain("formatted")` é o preferido para diagnóstico. `df.explain(True)` mostra parsed/analyzed/optimized logical e physical — útil pra ver o que o otimizador mudou. `df.explain("cost")` inclui estatística estimada. Gerar o plano é PySpark puro; redirecione a saída para um `.txt`, porque é o arquivo que o passo 2 consome.
2. **Extraia os facts do plano.**

   ```bash
   sparkforge analyze plan --path <plano>.txt --out .sparkforge/facts_plan.json
   ```

   Sai `plan.file_scan` (tabela particionada, `PartitionFilters` vazio, colunas de `ReadSchema` vs. referenciadas), `plan.join` (com e sem equi-condição), `plan.python_udf` (`BatchEvalPython`/`ArrowEvalPython`), `plan.exchange` e `plan.aqe`. O `subject` de cada fact é o **nó** do plano (`{"type": "plan_node", "symbol": "(1) Scan parquet db.tabela"}`), não a linha do arquivo de texto: o operador age sobre "a leitura de `db.tabela` no nó 1", e `file`/`line` acompanham só como procedência. Confira `unresolved` na saída antes de seguir.
3. **Leia de baixo para cima.** O plano executa das folhas (`Scan`) para a raiz. Percorra o checklist de `knowledge/spark/plan-reading.md` seção 6: `PartitionFilters` presente onde a tabela é particionada, `ReadSchema` só com as colunas usadas, contagem de `Exchange` justificável, ausência de `CartesianProduct`/`BroadcastNestedLoopJoin`, presença de `BatchEvalPython`/`ArrowEvalPython`, fan-out de `Generate`, estratégia de cada join confirmada (não só assumida).
4. **Nunca conclua estratégia de join só pelo `explain()`.** Com AQE ligado (default em Glue 4.0/5.x), o plano pode ser reescrito depois de cada shuffle. O plano final está na aba SQL do Spark UI, ou no event log real — não no `explain()` do código. `SF-PLAN-004` marca isso como achado próprio.
5. **Correlacione com o que o código pede.** `sparkforge analyze pyspark --path <arquivo ou diretório> --out .sparkforge/facts.json` extrai os facts estáticos por AST (`pyspark.join`, `pyspark.udf`, `pyspark.explode`, `pyspark.partitioning`, `pyspark.chain`, `pyspark.withcolumn_run`) que dão nome de arquivo e linha a cada operador suspeito do plano.
6. **Julgue os dois juntos.** `sparkforge judge --facts .sparkforge/facts_plan.json --facts .sparkforge/facts.json --show-skipped` aplica `SF-PLAN-*` e `SF-PQ-002`/`SF-PQ-004` sobre os facts do plano e o catálogo `SF-PY-*` (`rules/catalog/pyspark.yaml`) sobre os do código. `--facts` é repetível e `judge` une antes de julgar; passar os arquivos separados perde toda regra que correlaciona as duas fontes. Cada regra que dispara aponta um operador do plano e a linha exata de origem — é o passo que transforma "o Exchange 3 é caro" em "a linha 142 é o problema". Sem flag de versão: as regras `SF-PY-*` são estruturais, nenhuma declara `runtime_scope`, e os facts de AST não observam runtime — o campo `runtime` da saída volta vazio, com `detected_from: []`, e o que `--show-skipped` listar com `reason: runtime_scope` é infraestrutura Glue, fora do alcance deste `facts.json`. Isso importa nesta skill mais do que nas outras por um motivo: **a leitura do plano depende da versão e o motor não vai te cobrir aqui.** Se o AQE reescreveu o plano, quais operadores existem e quais defaults valem muda entre Glue 4.0 e 5.x, e nenhuma regra do catálogo guarda essa diferença. Confirme a versão numa fonte real antes de concluir — `sparkforge analyze terraform` e mais esse arquivo na mesma chamada fazem `runtime.detected_from` virar `["terraform"]`, e `--glue 5.1` serve quando você sabe a versão de fonte confiável e não tem o `.tf` à mão.
7. **Se há execução real, feche o ciclo.** `sparkforge analyze event-log --path <log> --out .sparkforge/facts.json` (procedimento completo em `analyze-spark-ui`) confirma se o operador suspeito do plano realmente custou — duração, spill, GC do stage correspondente àquele nó do plano.

## Do operador do plano à regra que o correlaciona

Duas tabelas, porque são dois caminhos diferentes. A primeira é o que o motor julga **direto do plano**; a segunda é a correlação estrutural entre o operador do plano e o fact estático de código que dá arquivo e linha — nessa segunda nenhuma linha tem limiar numérico, porque não é regra de execução.

## Referência rápida

Julgadas direto dos facts do plano (`sparkforge analyze plan`):

| Operador no plano | Regra | Fact que a regra consome |
|---|---|---|
| `Scan` de tabela particionada com `PartitionFilters` vazio | `SF-PQ-002` | `plan.file_scan` |
| `ReadSchema` muito maior que as colunas referenciadas | `SF-PQ-004` | `plan.file_scan` |
| `BatchEvalPython` (UDF Python pickled) | `SF-PLAN-001` | `plan.python_udf` |
| `ArrowEvalPython` (UDF vetorizada) | `SF-PLAN-002` | `plan.python_udf` |
| Join sem equi-condição (`CartesianProduct`, `BroadcastNestedLoopJoin`) | `SF-PLAN-003` | `plan.join` |
| Plano não-final do AQE | `SF-PLAN-004` | `plan.aqe` |

Correlacionadas ao código (`sparkforge analyze pyspark`), para ancorar o operador em arquivo e linha:

| Operador no plano | Regra `SF-PY` correlacionada | Fact que a regra consome |
|---|---|---|
| `BatchEvalPython` / `ArrowEvalPython` | `SF-PY-001` | `pyspark.udf` |
| `Exchange` antes de `Filter`/`Project` tardio | `SF-PY-003` | `pyspark.chain`, `pyspark.join` |
| `Generate` (explode) | `SF-PY-006` | `pyspark.explode` |
| Redução para uma única partição de saída | `SF-PY-005` | `pyspark.partitioning` |
| `BroadcastHashJoin` por hint fixo no código | `SF-PY-009` | `pyspark.join` |
| `Exchange` de repartition com argumento literal | `SF-PY-010` | `pyspark.partitioning` |
| Sequência longa de projeções antes do plano final | `SF-PY-007` | `pyspark.withcolumn_run` |

Limiares e severidade de cada regra vêm de `sparkforge rules lookup --id <ID>`, nunca de memória — o catálogo muda, e um número decorado vira mentira silenciosa.

## Quando NÃO usar

- Você já tem métricas de execução (Spark UI/event log) e quer o gargalo real: use `analyze-spark-ui`.
- Skew ou OOM já confirmados: aprofunde em `diagnose-data-skew` ou `diagnose-oom`.
- Ainda não tem o `explain`: gere com `df.explain("formatted")` antes de abrir esta skill.

## Red flags

- Afirmar causa (skew, spill, OOM) só pelo plano, sem métrica de task real.
- Tratar o plano exibido como o plano executado — ele pode ser o inicial, antes do AQE reescrever em runtime.
- Ler `sizeInBytes` do modo `cost` como verdade quando não há estatística atualizada na tabela.
- Ler `SF-PQ-004` como "sem achado" quando o plano veio com `... N more fields`: o extrator não conta lista truncada, emite `plan.unresolved` com `reason: truncated_field_list`, e a regra não é avaliada. Regenere o `explain` sem truncamento antes de concluir.
- Passar `df.explain("codegen")` ao extrator — é Java gerado, é rejeitado com `reason: unsupported_mode`, e a saída fica sem nenhum fact de plano.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
