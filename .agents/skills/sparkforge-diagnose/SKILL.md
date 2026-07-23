---
name: sparkforge-diagnose
description: Use quando precisar diagnosticar de ponta a ponta a performance de um job PySpark no AWS Glue — job lento, caro em DPU-hours, com OOM, falha intermitente, spill/shuffle alto ou small files — e ainda não sabe qual é o gargalo dominante, correlacionando código, plano físico, Spark UI, CloudWatch, S3, Parquet e Iceberg.
---

# SparkForge Diagnose

## Objetivo

Encontrar o gargalo dominante e produzir um plano de otimização baseado em evidências.

## Fluxo obrigatório

1. Leia `templates/job-intake.yaml` e preencha tudo que estiver disponível.
2. Determine Glue, Spark, Python e Iceberg efetivos.
3. Registre baseline: runtime, DPU-hours, bytes, shuffle, spill, memória e arquivos.
4. Analise o código com `checklists/code-review.md`.
5. Analise o plano físico, especialmente scans, filters, exchanges, joins, aggregates e sorts.
6. Analise Spark UI com `checklists/spark-ui.md`.
7. Analise CloudWatch e logs.
8. Analise S3/Parquet: bytes lidos, pruning, quantidade e distribuição de arquivos.
9. Se for Iceberg, analise snapshots, manifests, files, delete files, partições e manutenção.
10. Classifique gargalos por impacto e confiança.
11. Proponha experimentos isolados.
12. Produza relatório usando `templates/performance-report.md`.

## Classificação de gargalos

- CPU-bound
- Memory/GC-bound
- Shuffle-bound
- Skew-bound
- Driver-bound
- S3 I/O/listing-bound
- Small-files-bound
- Metadata-planning-bound
- Under-parallelized
- Over-partitioned
- Cluster-capacity
- Data-model/layout
- Iceberg maintenance debt

## Regras

- Não afirmar causalidade apenas por correlação.
- Não inventar percentuais de ganho.
- Não aumentar workers antes de avaliar redução de trabalho.
- Se faltarem métricas, declare a limitação e gere comandos/coletas necessárias.
- Diferencie plano inicial e plano final do AQE.
- Trate cada recomendação com o schema de `templates/recommendation.yaml`.

## Saída

1. Resumo executivo.
2. Baseline e limitações.
3. Gargalo dominante e evidências.
4. Gargalos secundários.
5. Recomendações P0–P4.
6. Código/configurações propostas.
7. Benchmark.
8. Validação funcional.
9. Riscos e rollback.

## Quando NÃO usar

- Investigação com fluxos full + incremental, latest-per-key e batching: comece por `glue-incremental-performance-architect`.
- Você já isolou o gargalo (skew, OOM, Iceberg, Terraform): vá direto à skill específica.
- Só quer revisar um trecho de código ou um PR: use `optimize-pyspark-code` ou `review-pyspark-pr`.

## Referência rápida

| Sintoma inicial | Direção provável | Primeira evidência a coletar |
|---|---|---|
| CPU baixa (<40%) + muito listing/S3 | Small files / I/O-bound | file count e tamanho médio por partição |
| Poucas tasks muito longas | Skew ou sub-paralelismo | max/median task time (razão > 3) |
| Spill alto (> input do stage) | Pressão de memória / partição grande | spill bytes vs input por task |
| GC > 15% do run time | Memory/GC-bound | GC time / executor run time |
| Runtime cresce a cada ciclo incremental | Scan global / falso incremental | bytes lidos vs volume da entrada |
| Falha após horas | OOM ou lineage/commits acumulados | exceção + componente + iteração |

## Red flags

- Recomendar mais workers ou mudar `spark.sql.shuffle.partitions` antes de ter baseline.
- Concluir causa a partir do plano sem métricas de execução.
- Reportar ganho percentual sem benchmark antes/depois.
- Ignorar validação funcional (contagem, schema, chaves, agregados) ao propor mudança.
