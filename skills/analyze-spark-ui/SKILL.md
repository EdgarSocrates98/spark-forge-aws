---
name: analyze-spark-ui
description: Use quando tiver screenshots, métricas ou event logs do Spark UI de um job Glue e precisar identificar o stage dominante, skew de task (max/median), spill, GC alto, fetch wait, stragglers, executors perdidos/ociosos ou gargalo de driver.
---

# Analyze Spark UI

## Procedimento

1. Identifique job run, duração e configuração.
2. Localize stages que dominam o runtime.
3. Compare mediana, p95 e máximo de duração das tasks.
4. Calcule ou estime:
   - max/median task duration;
   - coefficient of variation;
   - max/median input;
   - spill/input;
   - GC/executor run time.
5. Examine shuffle read/write e fetch wait.
6. Verifique scheduler delay e serialization.
7. Analise executors perdidos, ociosos ou desequilibrados.
8. Correlacione stage com o operador no SQL plan.
9. Produza hipóteses priorizadas e evidências faltantes.

## Heurísticas indicativas, não verdades universais

- Uma task muito maior que a mediana pode indicar skew.
- Spill alto pode indicar partições grandes, pressão de memória ou algoritmo inadequado.
- CPU baixa com leitura/listing elevada pode indicar I/O ou small files.
- Muitos tasks curtíssimos podem indicar excesso de partições.
- Poucos tasks longos podem indicar paralelismo insuficiente.
- Driver heap alto pode indicar metadata explosion ou operações no driver.

Use `checklists/spark-ui.md`.

## Quando NÃO usar

- Só tem o plano, sem métricas de execução: use `analyze-spark-plan`.
- O sintoma dominante é skew ou OOM: aprofunde em `diagnose-data-skew` ou `diagnose-oom`.
- Precisa de comparação controlada antes/depois: use `benchmark-pyspark-job`.

## Referência rápida

| Métrica do stage | Heurística de alerta | Hipótese |
|---|---|---|
| max task time / median | > 3 (e crescente) | skew de dados ou partição |
| spill (memory+disk) / input | > 1 | partição grande / pressão de memória |
| GC time / executor run time | > 15% | memory/GC-bound |
| shuffle read fetch wait | fração alta do task time | shuffle/rede ou stragglers |
| tasks por stage vs cores | << cores ativos | sub-paralelismo |
| duração média de task | muito baixa (ms) com milhares de tasks | over-partitioning / small files |

## Red flags

- Tratar uma única task lenta como o job todo sem olhar a distribuição (p50/p95/max).
- Confundir tempo ocioso por espera de I/O com falta de CPU.
- Ignorar executors perdidos/removidos (podem indicar OOM de container silencioso).
