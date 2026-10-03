# Flink streaming diagnostics

Esta página define o que um artefato offline de Apache Flink ou Managed Flink
pode provar. Ela não substitui logs do job, série temporal de métricas,
descrição do runtime ou validação funcional.

## Separação de domínios

`sparkforge analyze flink --artifact flink` lê fatos do Flink upstream:
`flink.job`, `flink.operator`, `flink.source`, `flink.sink`, `flink.checkpoint`
e `flink.state`. Source e sink são endpoints explícitos quando o dump traz
`sources`/`source` e `sinks`/`sink`; métricas como backlog, lag e commits
pendentes são preservadas somente quando observadas. O modo
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

## Sources e sinks

`flink.source` e `flink.sink` carregam identidade (`*_id`, nome, uid, tipo,
connector e delivery semantics) e medidas numéricas explicitamente presentes no
dump. `num_records_in`/`num_records_out` são contadores observados, não
throughput: sem timestamps e janela eles não permitem calcular taxa, latência
ou backlog drain.

Backlog/lag positivo em source e `pending_commits`/`commit_failures` em sink
devem ser correlacionados com uma série temporal, checkpoint, operador e
comportamento do connector antes de propor paralelismo ou mudança de sink. A
presença de `delivery_semantics: exactly_once` é declaração do artefato, não
prova de execução exactly-once.

Quando `sources`/`source` ou `sinks`/`sink` não aparecem, o extrator publica
`flink.unresolved` com `source_metrics_missing` ou `sink_metrics_missing`.
Formato inválido e registro vazio também têm razões nomeadas. Nenhuma medida
ausente é preenchida com zero.

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
4. Correlacionar checkpoint, operator, state, source, sink e transporte; trate
   `flink.source`/`flink.sink` como observações de endpoint, não como prova de
   saúde ou semântica de entrega.
5. Alterar uma variável principal por experimento, com rollback e proxies de
   contagem, schema, chave declarada e agregados.

## Coleta Managed Flink read-only

Para uma aplicação AWS, `sparkforge collect managed-flink` chama somente
`kinesisanalyticsv2.DescribeApplication` com `IncludeAdditionalDetails=false`.
O artifact local normaliza nome/ARN, status, runtime, versão da aplicação,
role, checkpoint, paralelismo, VPC, logging, localização do código sem copiar
`TextContent` e configuração de criptografia. O manifesto registra SHA,
comando de recoleta e cache offline-first.

```bash
sparkforge collect managed-flink --repo . --application-name orders \
  --region us-east-1 --now <ISO8601>
sparkforge analyze flink \
  --path .sparkforge/artifacts/managed_flink_application/orders__us-east-1.json \
  --artifact managed_flink
```

Esse collector é somente leitura na AWS e grava apenas o artifact/manifesto
local. `DescribeApplication` não é evidência de métricas temporais, job plan,
código executado, conectores efetivos, IAM efetivo ou latência; o artifact
publica `managed_flink_metrics_not_observed` e
`managed_flink_connectors_not_observed` como unresolved. Job plan exige uma
coleta explicitamente autorizada de detalhes adicionais; métricas exigem
CloudWatch/artefato temporal próprio.

## Fontes

* https://nightlies.apache.org/flink/flink-docs-stable/docs/learn-flink/fault_tolerance/
* https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/large_state_tuning/
* https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/metrics/
* https://docs.aws.amazon.com/managed-flink/latest/java/troubleshooting-checkpoints.html
* https://docs.aws.amazon.com/managed-flink/latest/java/metrics-dimensions.html
* https://docs.aws.amazon.com/managed-flink/latest/java/performance-monitoring.html
* https://docs.aws.amazon.com/managed-flink/latest/apiv2/API_DescribeApplication.html
