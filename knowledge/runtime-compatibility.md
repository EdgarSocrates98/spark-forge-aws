# Matriz de compatibilidade

Sempre confirme a documentação oficial e o runtime efetivamente usado pelo job.

| AWS Glue | Apache Spark | Python | Apache Iceberg embarcado |
|---|---:|---:|---:|
| 5.1 | 3.5.6 | 3.11 | 1.10.0 |
| 5.0 | 3.5.4 | 3.11 | 1.7.1 |
| 4.0 | 3.3.0 | 3.10 | 1.0.0 |
| 3.0 | 3.1.1 | 3.7 | 0.13.1 |

## Regras

- Não copiar configurações de Spark 4.x para Glue 5.x sem comprovar suporte.
- Não assumir que um procedimento ou propriedade da documentação `latest` do Iceberg existe na versão embarcada pelo Glue.
- Ao fornecer JARs próprios do Iceberg, revisar compatibilidade de Spark/Scala, precedência de classpath e parâmetros do Glue.
- Registrar no relatório a matriz detectada e qualquer divergência entre runtime embarcado e bibliotecas customizadas.
