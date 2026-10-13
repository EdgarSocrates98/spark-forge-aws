# Matriz de compatibilidade

> Versão expandida em [`glue/runtime-matrix.md`](glue/runtime-matrix.md): inclui Hudi,
> Delta, Scala, detecção de versão efetiva e conflito de JAR. Este arquivo permanece
> porque as 18 skills referenciam este caminho.

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
- Registrar no relatório a matriz detectada e qualquer divergência entre runtime embarcado e bibliotecas customizadas. É o finding `SF-ENV-001`.

## Três consequências que mudam recomendação

1. **AQE é default a partir do Spark 3.2** — logo, default em Glue 4.0 e 5.x, **não** em Glue 3.0 (Spark 3.1.1). Recomendar "o AQE cuida do skew" para Glue 3.0 é erro de versão. Regra `SF-ENV-004`.
2. **Iceberg format V3, que Glue 5.1 pode escrever, não é legível por Amazon Athena.** Havendo consumo por Athena, fixar `format-version = 2` ou permanecer em Glue 5.0. O modo de falha aparece no consumidor, dias depois. Regra `SF-ENV-002`.
3. **As métricas de escrita do Glue Observability não existem para tabelas Iceberg** (`recordsWritten`, `bytesWritten`, `filesWritten`). Medir escrita pelas metadata tables.

Conjunto completo dessas armadilhas em [`cross-service-constraints.md`](cross-service-constraints.md).
