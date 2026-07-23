# SparkForge AWS — Instruções do repositório

Ao trabalhar em código PySpark destinado ao AWS Glue:

1. Verifique a versão de Glue, Spark, Python e Iceberg antes de sugerir APIs ou configurações.
2. Não recomende tuning baseado somente no código; solicite ou produza plano físico e baseline quando possível.
3. Identifique o gargalo dominante: CPU, memória, GC, shuffle, skew, driver, S3, metadados, small files ou capacidade do cluster.
4. Priorize redução de trabalho e movimentação de dados antes de aumentar workers.
5. Prefira funções nativas Spark SQL a Python UDFs.
6. Não use `collect`, `toPandas`, `coalesce(1)`, `repartition` arbitrário ou `cache` indiscriminado.
7. Toda recomendação deve conter evidência, impacto esperado como hipótese, risco, validação e rollback.
8. Preserve semântica e valide contagens, schema, chaves, agregados e regras de negócio.
9. Para Iceberg, diferencie data files, delete files, manifests, snapshots e metadata files.
10. Nunca execute manutenção destrutiva sem confirmação explícita de escopo e retenção.

Use o agente `spark-performance-architect` para investigações abrangentes e as Skills específicas para tarefas focadas.


## Investigação avançada

Para jobs com fluxos full/incremental, use primeiro o agente `glue-incremental-performance-architect` e leia `PROMPT_INICIAL_MESTRE.md`. Não faça tuning localizado antes de mapear a biblioteca, actions, batching, latest-per-key e OOM.
