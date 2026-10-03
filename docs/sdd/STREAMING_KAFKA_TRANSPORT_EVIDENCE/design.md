---
sdd: 1
feature: STREAMING_KAFKA_TRANSPORT_EVIDENCE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_KAFKA_TRANSPORT_EVIDENCE/define.md
  sha256: "b9a42178563bce4fbe372641da60a7a7d8f5b36a787393226e752b68a6d4a837"
files:
  - {path: tests/test_facts_transport.py, action: modify, reason: "provar série explícita, timestamps fail-closed e guarda do snapshot legado"}
  - {path: sparkforge/facts/transport.py, action: modify, reason: "extrair lag_observations e compor kafka.lag.series sem nova superfície"}
  - {path: tests/test_streaming_rules.py, action: modify, reason: "provar condições observadas das duas regras novas"}
  - {path: rules/catalog/streaming_observability.yaml, action: modify, reason: "adicionar SF-STREAMOBS-003 e SF-STREAMOBS-004 com actions e fontes"}
  - {path: tests/test_fixtures_golden_transport.py, action: modify, reason: "incluir corpus Kafka novo no golden determinístico"}
  - {path: fixtures/transport/kafka_isr_deficit, action: create, reason: "golden positivo de replication factor maior que ISR"}
  - {path: fixtures/transport/kafka_lag_series, action: create, reason: "golden de série explícita crescente, não monotônica e timestamp inválido"}
  - {path: knowledge/transport-diagnostics.md, action: modify, reason: "documentar contrato de ISR e lag_observations, limites e fontes"}
  - {path: skills/review-streaming-operations/SKILL.md, action: modify, reason: "ensinar o especialista a extrair e julgar transporte Kafka sem causa presumida"}
  - {path: agents/streaming-realtime-architect.md, action: modify, reason: "rotear o coordenador para analyze transport e facts/rules Kafka"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "atualizar cobertura Kafka/MSK e lacunas live"}
  - {path: docs/guia/referencia/skills/review-streaming-operations.md, action: modify, reason: "referência gerada da skill após sincronização"}
  - {path: docs/DELIVERY-LEDGER.md, action: modify, reason: "registrar fase, provas e limites da entrega"}
  - {path: docs/EVOLUTION-CURRENT.md, action: modify, reason: "registrar evolução do diagnóstico Kafka"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "atualizar estado e números medidos"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "registrar hash do knowledge alterado"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "conferir fontes oficiais usadas pela regra e knowledge"}
  - {path: docs/surface.lock.json, action: modify, reason: "recontar knowledge/skills quando os docs mudarem"}
decisions:
  - id: D1
    choice: "`lag_observations` é uma entrada explícita; facts legados de consumer_groups/offsets continuam snapshot e não entram em série por ordem do arquivo."
    rejected: ["agrupar todos os kafka.lag por ordem de leitura", "consultar broker/MSK dentro do analyzer"]
    rollback: "Remover o bloco de composição e preservar o parser de kafka.lag legado; as regras novas deixam de ser alcançáveis até nova coleta."
  - id: D2
    choice: "Emitir um `kafka.lag.series` compacto por group/topic/partition, preservando observation fact ids e resumo numérico."
    rejected: ["emitir um fact por par temporal", "calcular p95, throughput ou drain rate nesta onda"]
    rollback: "Retirar somente o fact composto e manter as observações `kafka.lag` literais."
  - id: D3
    choice: "As rules comparam apenas replication_factor/isr_count e monotonic_increase/delta_lag observados; action pede baseline e não mutação."
    rejected: ["usar min.insync.replicas sem ele estar no artifact", "declarar indisponibilidade, perda ou causa do lag"]
    rollback: "Reverter as duas entradas de catálogo e os goldens de findings; facts permanecem válidos e sem julgamento."
covers:
  - {part: "extractor and compact series", acceptance: [AC1, AC2, AC3]}
  - {part: "catalog rules", acceptance: [AC4]}
  - {part: "fixtures", acceptance: [AC5]}
  - {part: "knowledge, skill and coordinator", acceptance: [AC6]}
---

# STREAMING_KAFKA_TRANSPORT_EVIDENCE — desenho

## Contrato de entrada

O formato novo é opcional e explícito:

```json
{
  "lag_observations": [
    {
      "group": "orders",
      "topic": "events",
      "partition": 0,
      "lag": 4,
      "observed_at": "2026-10-03T00:00:00Z"
    }
  ]
}
```

Cada identidade precisa de pelo menos dois pontos, timestamp textual
timezone-aware e lag numérico. Pontos inválidos produzem `kafka.unresolved`;
nenhum valor é preenchido. Uma série não monotônica ainda é observação válida,
mas não dispara `SF-STREAMOBS-004`.

## Conhecimento consultado

- `sparkforge rules lookup --category streaming_observability`: `SF-STREAMOBS`
  já roteia para `streaming-realtime-architect` e usa actions de baseline.
- `sparkforge/facts/transport.py`: facts Kafka existentes e envelope comum.
- Apache Kafka Basic Operations 4.0:
  `https://kafka.apache.org/40/operations/basic-kafka-operations/` — offsets,
  log end offset e lag no describe de consumer group.
- Apache Kafka Distribution:
  `https://kafka.apache.org/40/implementation/distribution/` — distribuição
  e réplica do log.
- `knowledge/transport-diagnostics.md`: limites de snapshot, unidade,
  identidade e ausência de causa.

## Economia de contexto

O analyzer mantém cada `kafka.lag` como evidência ancorada e acrescenta só um
resumo por identidade. A regra consome `kafka.lag.series`, sem reabrir o dump ou
duplicar cada par temporal em findings. Sem bloco explícito, nenhum fact de
tendência é criado.
