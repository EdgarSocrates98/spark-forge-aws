---
name: analyze-streaming-composition
description: "Use quando houver facts já extraídos de Structured Streaming e de Iceberg, Kafka ou Kinesis e for preciso correlacionar progresso, snapshots ou backlog sem escolher causa por intuição."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/streaming-lakehouse-observability.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge analyze streaming-composition
  - sparkforge judge
subagent: true
---

# Analyze Streaming Composition

Esta skill trabalha sobre Facts existentes. Ela não consulta AWS, Kafka, Spark
ou Iceberg e não substitui a extração dos artefatos.

## Procedimento

1. Extraia os lados separadamente e grave os Facts:

```bash
sparkforge analyze streaming --path progress.jsonl --artifact progress --out progress.facts.json
sparkforge analyze iceberg --path iceberg.json --out iceberg.facts.json
sparkforge analyze transport --path kafka.json --artifact kafka --out transport.facts.json
```

2. Declare a identidade que prova que os artefatos pertencem ao mesmo caminho.
Para streaming→Iceberg, informe tabela e query. Para progresso→transporte,
informe grupo/topic Kafka ou stream Kinesis:

```bash
sparkforge analyze streaming-composition \
  --facts progress.facts.json --facts iceberg.facts.json \
  --mode iceberg --table db.events --query-name orders-query \
  --out composed.facts.json

sparkforge analyze streaming-composition \
  --facts progress.facts.json --facts transport.facts.json \
  --mode observability --query-name orders-query --transport-key orders-group \
  --out composed.facts.json

sparkforge analyze streaming-composition \
  --facts progress.facts.json --facts transport.facts.json \
  --mode temporal --query-name orders-query --transport-key orders-group \
  --max-skew-seconds 3 --out temporal.facts.json

sparkforge analyze streaming-composition \
  --facts progress.facts.json --facts iceberg.facts.json \
  --mode iceberg_temporal --table db.events --query-name orders-query \
  --max-skew-seconds 3 --out iceberg-temporal.facts.json

sparkforge analyze streaming-composition \
  --facts slo-contract.facts.json --facts progress.facts.json \
  --mode slo --slo-name throughput --query-name orders-query \
  --out slo-evaluation.facts.json

sparkforge analyze streaming-composition \
  --facts slo-contract.facts.json --facts kafka.facts.json \
  --mode slo --slo-name consumer-lag --transport-key orders-group \
  --out transport-slo.facts.json

sparkforge analyze streaming-composition \
  --facts slo-contract.facts.json --facts progress.facts.json \
  --mode slo --slo-name sink-output --query-name orders-query \
  --out sink-slo.facts.json
```

3. Para `mode=temporal` e `mode=iceberg_temporal`, `max-skew-seconds` é
   obrigatório como declaração do chamador. O compositor só usa timestamps
   observados; ordem do arquivo, relógio local e tolerância implícita não contam.

4. Leia `streaming.composition.unresolved` e `streaming.temporal.unresolved`
   antes de julgar. Query, tabela, grupo, stream, timestamp ou janela ausente
   é ponto cego; não vira zero nem “saudável”.

Para `mode=slo`, `source` Structured Streaming exige query e métrica diretamente
observada em `streaming.progress.batch`. `source: streaming_sink` exige query e
avalia `num_output_rows` diretamente observada em `streaming.progress.sink`;
o `batch_id` liga cada saída ao timestamp do batch correspondente. `sink_name`
é opcional quando há uma única descrição e desambigua descrições distintas.
`source: kafka` exige
`--transport-key` e lê `kafka.lag`; `source: kinesis` exige a mesma identidade
e lê `kinesis.shard`. Kafka usa `lag`/`records`; Kinesis usa
`iterator_age_ms`/`ms`. Em todos os casos, exige unidade canônica, pelo menos
duas observações timestampadas e span observado igual ou maior que a janela
declarada. `streaming.slo.evaluation` informa `met` ou `violated`;
`streaming.slo.unresolved` informa a barreira sem transformar ausência em
sucesso. `SF-STREAM-011` julga violação observada; `SF-STREAM-012` julga a
lacuna estrutural. `statistic: p95` publica `observed_p95` por nearest-rank
`ceil(0.95*n)`; `freshness_ms` usa `timestamp - eventTime.max` quando ambos
estão válidos, e end-to-end latency exige medida explícita. O compositor não
agrega grupos/shards/sinks, converte unidades, usa ordem do arquivo ou consulta
CloudWatch/Kafka live.

5. Julgue o arquivo composto:

```bash
sparkforge judge --facts composed.facts.json --show-skipped
```

## Interpretação

`SF-STREAMICE-001` significa operação não-append observada no vínculo
declarado. Não significa que a query falhou. Confirme leitura incremental,
consumidores, replay e retenção de snapshots antes de qualquer manutenção.

`SF-STREAMOBS-001` significa que uma série de processamento abaixo da entrada
coexiste com lag/iterator age observado no transporte declarado. Não é root
cause. Colete timestamps pareados, duração de trigger, state, sink, throttling e
resultado funcional antes de escolher uma mudança.

`SF-STREAMOBS-002` exige pelo menos dois pares temporais completos, dentro da
tolerância declarada, com processamento abaixo da entrada e backlog/idade
observados. É evidência de coexistência na janela; não identifica causa, SLO,
custo ou ganho de capacidade.

`mode=iceberg_temporal` produz `iceberg.snapshot` granular e
`streaming.iceberg.temporal` somente quando há pelo menos dois pares entre
`StreamingQueryProgress` e `committed_at` do Iceberg. `SF-STREAMICE-002`
indica operação não-append observada nessa janela; `causal_inference: false`
permanece explícito. Valide replay, leitura incremental, consumidores e
resultado funcional antes de alterar o sink.

`mode=slo` só produz avaliação resolvida quando a janela declarada foi coberta
por facts de progress ou transporte compatível. `met` significa que todos os valores observados
passaram pelo comparador; não significa disponibilidade, saúde end-to-end,
causa, custo ou atendimento fora do artefato fornecido.

## Limites

- uma amostra não prova tendência;
- lag ausente não é lag zero;
- snapshot por observação não é automaticamente defeito;
- checkpoint não prova exactly-once end-to-end;
- correlação não prova causalidade;
- ausência de finding não prova saúde.
- snapshot agregado não substitui a observação granular de cada snapshot;
- timestamp sem timezone, timestamp ausente ou par fora da janela produz
  `streaming.temporal.unresolved` ou `streaming.composition.unresolved`,
  conforme o modo;
- use `--detail-level summary` para triagem barata e reexecute `full` apenas
  quando precisar dos facts/proveniências, mantendo `source_fact_ids` para
  reauditoria.
- `streaming.slo.unresolved` deve ser reportado mesmo quando não há finding de
  violação; ausência de finding não prova SLO atendido.

Toda recomendação mantém risco, trade-off, validação e rollback. Nenhuma
alteração live ou manutenção destrutiva pertence a esta skill.

## Contrato de qualidade SparkForge (v1)

- **Entrada mínima:** Facts de origem, runtime/contexto quando aplicável e
  identidade declarada do vínculo.
- **Evidência:** cada finding aponta `fact_id`; Facts compostos carregam
  `source_fact_ids` e procedência dos artefatos.
- **Validação:** confirmar janela, unidade, identidade, consumidores e proxies
  funcionais; reportar todos os unresolved.
- **Segurança:** não executar collector ou escrita AWS; propor somente ações
  reversíveis com rollback explícito.

validation deve ser registrada literalmente no handoff; rollback deve apontar a
reversão concreta da recomendação.

## Quando NÃO usar

Não use sem Facts compatíveis ou quando a pergunta exigir benchmark, causalidade
ou estado live de Kafka, Kinesis, Spark ou Iceberg.

## Referência rápida

Identidade declarada vincula os lados; `fact_id` ancora cada observação e
`*.unresolved` impede preencher um campo ausente.

## Red flags

Mesmo nome de query, tabela ou tópico não prova que os artefatos pertencem ao
mesmo caminho; ausência de finding não prova saúde.

## Protocolo

Siga `AGENT_PROTOCOL.md`, não executa manutenção destrutiva; sobe qualquer
mutação ao operador.

## Runtime e escopo

Rode `sparkforge judge --facts <facts.json> --show-skipped` e leia `runtime`,
`detected_from`, `divergences` e `reason: runtime_scope`. Runtime deve vir de
facts reextraídos ou de versão concreta declarada; não invente versão. Regras
fora do `runtime_scope` são recusadas/puladas, não equivalem a ausência de finding.
