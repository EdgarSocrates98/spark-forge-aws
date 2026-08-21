# SparkForge AWS — Interactive Demos & Walkthroughs (Phase 11)

Demonstrações práticas mostrando o funcionamento da **Data & AWS Agent Factory**, com destaque para roteamento por capacidade, economia de tokens e extração determinística de evidências.

---

## Demo 1: Otimização de Job Glue PySpark com Skew de Memória

### Cenário
Um job AWS Glue 4.0 processando 500GB apresenta lentidão severa e OOM intermitente em um executor específico.

### Execução na Factory
```bash
# 1. Inspeção sem gastar tokens LLM (Tier 0)
sparkforge analyze pyspark --path examples/glue_iceberg_job.py --out facts.json

# 2. Julgamento determinístico contra o catálogo
sparkforge judge --facts facts.json --catalog rules/catalog/

# 3. Roteamento por Capacidade
# Rota Selecionada: Tier 4 (Specialist Model)
# Skills Injetadas: optimize-pyspark-code, diagnose-data-skew
# Perfil: ECO
# Consumo Estimado: ~2.400 tokens ($0.003 USD) vs ~45.000 tokens em multi-agent genérico
```

---

## Demo 2: Desenho de Pipeline CDC Serverless na AWS

### Cenário
Desenhar arquitetura de Change Data Capture (CDC) do DynamoDB / RDS para Apache Iceberg no S3 via Kinesis e Glue Streaming.

### Execução na Factory
- **Rota**: `Tier 4 (Specialist Model)`
- **Skills Carregadas (Progressive Disclosure)**: `streaming-reliability`, `optimize-iceberg-tables`, `data-contracts-schema-evolution`
- **Output**: Especificação de arquitetura, sizing de DPU e políticas IAM com privilégio mínimo.

---

## Demo 3: Análise de Mudança de Schema em Tabela Iceberg

### Cenário
Evolução de schema adicionando colunas e modificando tipos em tabela Iceberg com 50 consumidores downstream.

### Execução na Factory
- **Camada Determinística**: `sparkforge analyze catalog-schema` + `sparkforge analyze consumers`
- **Rota**: `Tier 0 (Deterministic First)` — Cálculo de compatibilidade de schema 100% determinístico.
- **Tokens Consumidos**: 0 tokens LLM.

---

## Demo 4: Redução de Custos em Workload Spark no EMR (FinOps)

### Cenário
Cluster EMR on EC2 com custo mensal elevado devido a instâncias On-Demand e provisionamento estático.

### Execução na Factory
- **Rota**: `Tier 4 (Specialist)`
- **Skills Carregadas**: `review-emr-cluster`, `data-platform-finops`
- **Recomendações Emitidas**: Conversão de Task nodes para Instance Fleets com Spot, ativação de Managed Scaling com `MinimumCapacityUnits`, e fine-tuning de spill em EBS.

---

## Demo 5: Investigação de Falha Crítica em Job Glue (RCA)

### Cenário
Job falhou com `Container killed by YARN for exceeding memory limits`.

### Execução na Factory
- **Extração**: `sparkforge analyze event-log --path event_log.jsonl`
- **Resultado do Julgamento**: Fato `eventlog.executor_oom` correlacionado com `pyspark.skew_join` (Regra `SF-PY-002`).
- **Relatório**: Emitido com assinatura criptográfica SHA-256 e plano de rollback testável.
