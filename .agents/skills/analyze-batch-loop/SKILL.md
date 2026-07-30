---
name: analyze-batch-loop
description: Use quando o job processa dados em lotes com for/while, collect de chaves, isin(list) gigante ou filtros por batch id, ou dispara action/write/count/merge dentro de loop, e você suspeita de recomputação do DAG, lineage crescente, múltiplos commits Iceberg ou OOM acumulado por iteração.
---

# Analyze Batch Loop

## Localizar

- `for` e `while`;
- `collect`;
- `toLocalIterator`;
- `.rdd`;
- listas de chaves;
- `isin(list)`;
- `limit` + subtract;
- filtros por batch id;
- actions dentro de loop;
- `count`, `show`, `write`, `save`, `append`, `merge`;
- cache/persist/checkpoint dentro de loop;
- DataFrames armazenados em coleções;
- funções chamadas por lote.

## Pergunta principal

> O batch reduz o scan e o shuffle desde a origem, ou o Spark recompõe o pipeline caro para cada action?

## Diagnóstico

Para cada lote, estime:
- scans repetidos;
- exchanges repetidos;
- joins repetidos;
- ações;
- commits;
- snapshots;
- arquivos;
- lineage;
- objetos mantidos no driver;
- tempo acumulado.

## Recomendações possíveis

- remover batching lógico;
- usar particionamento Spark real;
- materializar uma etapa intermediária comprovadamente útil;
- escrever uma vez;
- usar batch id como coluna distribuída;
- processar hot keys separadamente;
- desacoplar regras;
- checkpoint somente quando necessário;
- consolidar commits;
- usar staging table.

## Saída

Mapa do loop, custo por iteração, causa do crescimento, refatoração e benchmark.

## Quando NÃO usar

- Não há loop; o custo é de uma única passada: use `analyze-spark-plan`/`analyze-spark-ui`.
- O batching estoura memória e você precisa classificar o OOM: combine com `diagnose-oom`.
- O objetivo é desenhar o incremental de forma correta: use `design-incremental-processing`.

## Referência rápida

| Padrão no loop | Por que dói | Refatoração |
|---|---|---|
| `write`/`append`/`merge` por iteração | N commits, snapshots e small files | acumular e escrever/commitar uma vez (staging) |
| `count`/`show` por iteração | recomputa o DAG caro a cada action | remover ou medir uma vez fora do loop |
| `collect` de chaves + `isin(list)` | driver carrega tudo; filtro não faz pruning | join distribuído por tabela de chaves |
| `cache` dentro do loop sem `unpersist` | memória cresce por iteração | materializar fora; liberar entre iterações |
| DataFrames acumulados em lista | lineage/plano crescente | `checkpoint` pontual ou reescrever a lógica |

## Red flags

- Assumir que `isin(lista_de_chaves)` garante file pruning (geralmente não garante).
- "Batching" que apenas filtra um DAG caro antes de cada action, sem reduzir trabalho na origem.
- Muitos commits Iceberg por lote gerando explosão de snapshots/manifests.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
