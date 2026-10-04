---
name: review-structured-streaming
description: "Use quando houver código Structured Streaming, StreamingQueryProgress ou metadados de checkpoint e for preciso separar declaração estática, medida temporal, runtime e resultado funcional."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/streaming-reliability.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge analyze streaming
  - sparkforge analyze pyspark
  - sparkforge analyze streaming-integrations
  - sparkforge judge
---

# Review Structured Streaming

Use esta skill para revisar uma query Structured Streaming sem confundir o que
o código declara com o que uma execução mediu. O fluxo é offline e trabalha
somente com artefatos salvos.

## Procedimento

1. Rode `sparkforge analyze streaming --artifact source --path <job.py-ou-dir>`
   para source, sink, trigger, checkpoint, watermark, joins, deduplicação,
   state e `foreachBatch` declarados.
2. Rode `sparkforge analyze streaming --artifact progress --path <progress.jsonl-ou-dir>`
   para batches, input/processed rate, duração, event time, sink e state
   observados. O fact `streaming.progress.series` também resume, quando completos,
   span temporal, duração de batch, memória total do state e watermark. Quando
   `eventTime.max` e `timestamp` são timezone-aware, cada batch pode publicar
   `freshness_ms`; `end_to_end_latency_ms` só aparece se o progress o declarar
   explicitamente. Série insuficiente deve permanecer `streaming.progress.unresolved`.
3. Quando houver checkpoint ou integrações declaradas, rode
   `sparkforge analyze streaming-integrations --path <dump.json-ou-dir>`.
   Metadados internos de checkpoint só podem ser interpretados quando formato
   e versão forem observáveis; não parseie layout interno por suposição.
4. Confirme runtime/version antes de julgar regras versionadas. Depois rode
   `sparkforge judge --facts <facts...> --show-skipped` e leia os motivos dos
   rules que ficaram fora de escopo ou sem evidência.
5. Correlacione query, progresso, transporte, checkpoint, sink e validação
   funcional. `processedRowsPerSecond < inputRowsPerSecond`, `watermark_stalled`
    e `state_memory_growth_observed` são sintomas observados, não causas; duas
    amostras não provam tendência de longo prazo. Para SLO, `statistic=p95`
    usa nearest-rank `ceil(0.95*n)` sem interpolação; leia `observed_p95` como
    resumo da amostra, não como prova de saúde live.
6. Para qualquer mudança, defina uma variável primária, baseline, contagem,
   schema, chave e agregados de validação, risco e rollback. Não alegue ganho,
   custo, throughput ou exactly-once sem evidência compatível.

## Limites

- Não chama Spark, AWS, Kafka ou Flink; coleta viva pertence ao operador e aos
  collectors read-only disponíveis.
- Não transforma ausência de checkpoint, watermark, offset, sink ou métrica em
  zero; emita ou preserve `*.unresolved`.
- Não transforma `watermark_stalled` em freshness violada nem crescimento de
  memória em leak; ambos exigem contexto e validação adicionais. Freshness só
  é comparada quando `timestamp` e `eventTime.max` estão pareados e válidos.
- Código estático não prova backlog, latência, capacidade, semântica end-to-end
  nem resultado funcional.
- Não recomenda intervalo de trigger, número de partições, workers ou state TTL
  por regra fixa sem requisito, runtime e medida.
- Não declara exatamente-once para a arquitetura inteira a partir de uma
  garantia local do engine ou do sink.

## Entrega

Retorne facts, findings, unresolved, hipótese e recomendação separados. Cada
finding precisa de `fact_id` e `rule_id`. Cada recomendação usa `validation` e
`rollback` completos e nomeia o artefato que destrava qualquer decisão ainda
unresolved.

## Quando NÃO usar

Use `review-glue-streaming` quando a pergunta for a definição de Glue/RTM;
`analyze-flink-job` para artefato Flink; e
`analyze-streaming-composition` quando a decisão depender de transporte,
Iceberg, serving ou observabilidade correlacionados.

## Protocolo

Siga `AGENT_PROTOCOL.md`: preserve procedência, valide a saída e reporte
blind spots. Antes de fechar uma recomendação, derive validação funcional com
`funcval plan` quando a mudança puder alterar dados e compare o antes/depois
com `funcval compare`. O subagente não executa manutenção destrutiva; sobe qualquer mudança
externa ao operador responsável.

## Referência rápida

`streaming.progress.series` exige série válida; `streaming.progress.unresolved`
nomeia ausência ou medida temporal inválida. Static source facts não são
medidas de execução. `streaming.slo` aceita `statistic=all|p95`,
`freshness_ms` e latência end-to-end apenas quando observadas. `SF-STREAM-013`
e `SF-STREAM-014` consomem somente os flags observados de watermark e memória,
com runtime fact presente.

## Red flags

Uma amostra não é tendência; checkpoint configurado não é replay provado; taxa
processada menor não identifica causa; exactly-once local não é garantia
end-to-end.

## Contrato de qualidade SparkForge (v1)

Facts offline sustentam diagnóstico; cada finding precisa de `fact_id` e
`rule_id`; recomendações mantêm `validation` e `rollback`; ausência de dado
continua `*.unresolved`.

## Runtime e escopo

Rode `sparkforge judge --facts <facts.json> --show-skipped` e leia `runtime`,
`detected_from`, `divergences` e `reason: runtime_scope`. Runtime deve vir de
facts reextraídos ou de versão concreta declarada; não invente versão. Regras
fora do `runtime_scope` são recusadas/puladas, não equivalem a ausência de finding.
