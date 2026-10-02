# Streaming operations: SLO, FinOps e segurança

O analyzer `analyze streaming-ops` lê contrato JSON salvo e produz facts para
cinco eixos: SLO, FinOps, security, serving e lakehouse. Ele mede declaração,
não prova execução. `unresolved` é obrigatório quando target, contexto de
custo ou controle de segurança não aparecem.

## SLO

Declaração mínima: métrica, target, operador, unidade, janela e fonte. Exemplos
úteis são p95 end-to-end latency, freshness, lag máximo, RPO, RTO,
disponibilidade e tolerância a perda. O Forge não escolhe `X`, não interpreta
ausência como sucesso e não compara séries com janelas ou unidades diferentes.

### Avaliação offline observada

`sparkforge analyze streaming-composition --mode slo` compõe uma declaração
`streaming.slo` com `streaming.progress.batch` já extraído. A composição exige
`--query-name`, seleciona `--slo-name` quando há mais de uma declaração e aceita
somente métricas diretamente presentes no progress: `input_rows_per_second`,
`processed_rows_per_second`, `batch_duration_ms` e `num_input_rows`.

Para emitir `streaming.slo.evaluation`, a unidade precisa ser compatível, o
operador precisa ser `lt`, `lte`, `gt`, `gte` ou `eq`, há pelo menos duas
observações timestampadas e o span observado cobre a janela declarada (`s/m/h/d`).
O status `met` significa que todos os valores observados passaram no comparador;
`violated` significa que ao menos um não passou. O fact preserva
`source_fact_ids`, extremos, contagem, janela e `causal_inference: false`.

Declaração, identidade, source, métrica, unidade, timestamp, quantidade ou
cobertura ausente produzem `streaming.slo.unresolved`. O Forge não calcula p95
de uma taxa, não converte unidade, não usa nome de janela como prova de
cobertura e não consulta CloudWatch/Kafka live. `SF-STREAM-011` julga somente
violação observada; `SF-STREAM-012` torna a lacuna explícita. Nenhum dos dois
atribui causa, custo, disponibilidade ou resultado funcional.

## FinOps

Separar três perguntas:

1. qual uso/custo foi medido;
2. a qual workload ou camada ele pode ser atribuído;
3. qual hipótese de otimização será testada.

Para comparação, preservar unidade, período, região, tier e fonte. A resposta
de custo exato depende de preço vigente, região e uso; não há preço hard-coded
nesta base. Dimensões de streaming incluem worker-hours Glue, KPUs Managed
Flink, brokers/partitions MSK, shards/EFO Kinesis, storage, transferência,
cross-AZ/cross-Region, manutenção Iceberg e consumidores Redshift.

## Segurança e redaction

Revisar separadamente IAM, resource policy, KMS, TLS/SASL/mTLS, VPC/endpoints,
Secrets Manager, ACL, execution role e cross-account. IAM simulation não
substitui bucket policy, KMS key policy ou política do serviço. O extractor não
persiste valores de chaves que pareçam senha, token, credential, secret ou
private key; registra somente unresolved do caminho sanitizado.

## Fontes

- [Spark Structured Streaming Programming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [AWS Cost and Usage Reports](https://aws.amazon.com/aws-cost-management/aws-cost-and-usage-reporting/)
- [Amazon MSK authentication and authorization](https://docs.aws.amazon.com/msk/latest/developerguide/msk-authentication.html)
- [Amazon Kinesis PutRecord API](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_PutRecord.html)
- [AWS IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
