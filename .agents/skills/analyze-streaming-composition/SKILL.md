---
name: analyze-streaming-composition
description: "Use quando houver facts já extraídos de Structured Streaming e de Iceberg, Kafka ou Kinesis e for preciso correlacionar progresso, snapshots ou backlog sem escolher causa por intuição."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/streaming-lakehouse-observability.md
  primary_verbs:
  - sparkforge analyze streaming-composition
  - sparkforge judge
subagent: true
agent: streaming-realtime-architect
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
```

3. Leia `streaming.composition.unresolved` antes de julgar. Query, tabela,
grupo, stream ausente ou ambíguo é ponto cego; não vira zero nem “saudável”.

4. Julgue o arquivo composto:

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

## Limites

- uma amostra não prova tendência;
- lag ausente não é lag zero;
- snapshot por observação não é automaticamente defeito;
- checkpoint não prova exactly-once end-to-end;
- correlação não prova causalidade;
- ausência de finding não prova saúde.

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
