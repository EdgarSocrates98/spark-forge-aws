# Flink streaming diagnostics

Esta página define o que um artefato offline de Apache Flink ou Managed Flink
pode provar. Ela não substitui logs do job, série temporal de métricas,
descrição do runtime ou validação funcional.

## Separação de domínios

`sparkforge analyze flink --artifact flink` lê fatos do Flink upstream:
`flink.job`, `flink.operator`, `flink.checkpoint` e `flink.state`. O modo
`--artifact managed_flink` usa `managed_flink.application`,
`managed_flink.config`, `managed_flink.connector` e `managed_flink.metric`.
Os namespaces não são intercambiáveis: um dump do serviço gerenciado não
completa o runtime upstream, e o contrário também não.

## Checkpoints e state

Um checkpoint observado com status `FAILED` prova falha naquela observação. Não
prova a causa, a duração total do incidente ou o resultado escrito. Correlacione
id, status, duração, alignment, tamanho de state, logs e política de restart.

Checkpoint e savepoint registram estado, mas semântica de processamento,
entrega do sink e idempotência continuam dependentes do job e dos conectores.
Não declare exactly-once só porque existe checkpoint.

## Backpressure

Uma medida positiva de `backpressured_ratio` ou `backpressured_ms` é sinal
observado no operador. Não é limiar universal de incidente. Compare janela,
unidade, busy/idle time, throughput, backlog e operador downstream. Backpressure
transitório, skew, rede e sink lento podem produzir leituras parecidas.

## Ausência de evidência

Métrica ausente vira `flink.unresolved` ou `managed_flink.unresolved`, nunca
zero. Sem runtime, janela, origem, unidade ou série comparável, a conclusão deve
ser unresolved e nomear o artefato que destrava a pergunta.

## Procedimento

1. Salvar o dump e registrar origem, instante e runtime.
2. Rodar `sparkforge analyze flink` no domínio correto.
3. Conferir unresolved e procedência antes de `sparkforge judge`.
4. Correlacionar checkpoint, operator, state, source, sink e transporte.
5. Alterar uma variável principal por experimento, com rollback e proxies de
   contagem, schema, chave declarada e agregados.

## Fontes

* https://nightlies.apache.org/flink/flink-docs-stable/docs/learn-flink/fault_tolerance/
* https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/large_state_tuning/
* https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/metrics/
* https://docs.aws.amazon.com/managed-flink/latest/java/troubleshooting-checkpoints.html
* https://docs.aws.amazon.com/managed-flink/latest/java/metrics-dimensions.html
* https://docs.aws.amazon.com/managed-flink/latest/java/performance-monitoring.html
