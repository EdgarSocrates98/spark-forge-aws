---
sdd: 1
feature: FORGE_LAB_DIGITAL_TWIN
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Blueprint local declarativo com Compose profiles, topologia e cenários de falha sem ações destrutivas implícitas."
    tradeoffs: ["reprodutível e auditável", "imagens e credenciais continuam responsabilidade do operador"]
  - id: B
    summary: "Harness que controla Docker diretamente a partir do CLI."
    tradeoffs: ["automatiza mais", "mistura análise offline com mutação de infraestrutura local"]
chosen: A
---

# FORGE_LAB_DIGITAL_TWIN — exploração

Pedido explícito do prompt escolhe um laboratório local como produto do
SparkForge, com Kafka, Flink, Spark, Iceberg REST, Polaris, MinIO/S3,
PostgreSQL/Debezium e Prometheus. A abordagem A mantém o plano de falha como
declaração auditável; nenhum comando do analisador mata processo, publica evento
ou altera tabela.
