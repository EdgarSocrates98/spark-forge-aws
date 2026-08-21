# SparkForge AWS — AWS Data Platform Capability Matrix (Phase 0)

Mapeamento de 20 serviços fundamentais de dados da AWS em 10 dimensões de engenharia:

| Serviço AWS | Architecture | Dev / Code | Terraform | Security & IAM | FinOps / Cost | Observability | Troubleshooting | Migration | Performance | Testing & Evals |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **AWS Glue** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (4.0➔5.1) | ✅ | ✅ |
| **Lake Formation**| ✅ | ✅ | ✅ | ✅ (FGAC/FTA)| ✅ | ✅ | ✅ (Cross-Acc) | ✅ | ✅ | ✅ |
| **Apache Iceberg**| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Doctor) | ✅ (v1/v2/v3) | ✅ (Compaction)| ✅ |
| **Amazon S3** | ✅ | ✅ | ✅ | ✅ (Public Block)| ✅ (Tiering)| ✅ | ✅ (S3A/EMRFS) | ✅ | ✅ | ✅ |
| **Amazon Athena** | ✅ | ✅ | ✅ | ✅ (Workgroups)| ✅ (Scanned)| ✅ | ✅ | ✅ (Engine v3) | ✅ (Projection)| ✅ |
| **Amazon EMR EC2**| ✅ | ✅ | ✅ | ✅ | ✅ (Spot Fleets)| ✅ | ✅ | ✅ (6.x➔7.x) | ✅ (AQE/Spill) | ✅ |
| **EMR Serverless**| ✅ | ✅ | ✅ | ✅ | ✅ (Auto-stop)| ✅ | ✅ | ✅ | ✅ | ✅ |
| **Amazon Redshift**| ✅ | ✅ | ✅ | ✅ | ✅ (Serverless)| ✅ | ✅ | ✅ | ✅ (WLM/Sort) | ✅ |
| **Amazon DynamoDB**| ✅ | ✅ | ✅ | ✅ | ✅ (On-Demand)| ✅ | ✅ (Hot Part) | ✅ | ✅ (Adaptive) | ✅ |
| **Amazon Neptune**| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Explain) | ✅ (Neo4j➔Nept)| ✅ (Bulk Load) | ✅ |
| **Amazon MSK** | ✅ | ✅ | ✅ | ✅ (mTLS/IAM)| ✅ | ✅ | ✅ (Lag/Rebal) | ✅ | ✅ | ✅ |
| **Amazon Kinesis**| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Hot Shards)| ✅ | ✅ (Fan-out) | ✅ |
| **AWS DMS** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (CDC/Full) | ✅ | ✅ |
| **Step Functions**| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Retries) | ✅ | ✅ (Dist Map) | ✅ |
| **AWS Lambda** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Concurrency)| ✅ |
| **EventBridge** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **SQS / SNS** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (DLQ/Replay) | ✅ | ✅ | ✅ |
| **Glue Schema Reg**| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Evolution) | ✅ | ✅ | ✅ |
| **IAM & KMS** | ✅ | ✅ | ✅ | ✅ (Least Priv)| ✅ | ✅ (CloudTrail)| ✅ | ✅ | ✅ | ✅ |
| **CloudWatch/Trail**|✅ | ✅ | ✅ | ✅ | ✅ (Retention)| ✅ | ✅ (Timeline) | ✅ | ✅ | ✅ |
