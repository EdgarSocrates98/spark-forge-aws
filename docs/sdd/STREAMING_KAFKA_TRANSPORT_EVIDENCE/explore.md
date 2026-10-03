---
sdd: 1
feature: STREAMING_KAFKA_TRANSPORT_EVIDENCE
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Ampliar o analyzer offline de transporte com ISR observado e série Kafka explícita de lag, reutilizando facts, rules e skill existentes."
    tradeoffs:
      - "fecha dois sinais operacionais úteis sem criar superfície ou dependência live"
      - "exige contrato explícito para timestamps e identidade da série"
  - id: B
    summary: "Adicionar collector Kafka/MSK live para broker, grupo e métricas temporais."
    tradeoffs:
      - "poderia observar estado atual do serviço"
      - "exige endpoint, credencial, segurança, paginação e novo contrato de coleta"
  - id: C
    summary: "Inferir saúde, hot partition ou tendência a partir do snapshot Kafka existente."
    tradeoffs:
      - "menor alteração de código"
      - "confunde observação pontual com causa, série ou limiar operacional"
chosen: A
---

# STREAMING_KAFKA_TRANSPORT_EVIDENCE — exploração

## Perfil

`dev`: a mudança é no próprio SparkForge. O objetivo maior exige utilidade para
engenharia de dados real, preservando economia de contexto e o contrato
evidence-first do repositório.

## Evidência consultada

- `sparkforge sdd status --repo .`: `STREAMING_TRANSPORT_DIAGNOSTICS` já emite
  `kafka.partition` e `kafka.lag`, mas registra que regras com baseline e série
  continuam pendentes.
- `sparkforge/facts/transport.py`: o extrator preserva `replication_factor`,
  `isr_count`, offsets, lag e timestamps existentes, sem composição de série.
- `knowledge/transport-diagnostics.md` e `docs/streaming/prompt-coverage.md`:
  snapshot de transporte não prova hot partition, causa ou tendência longa.
- Documentação oficial Apache Kafka: `kafka-topics --describe` expõe replicas e
  ISR por partição; `kafka-consumer-groups --describe` expõe current offset,
  log end offset e lag.

## Abordagens

- **A — especialização offline no analyzer existente.** Comparar somente os
  campos observados `replication_factor`/`isr_count`. Para lag, aceitar apenas
  `lag_observations` explícito, com group/topic/partition, lag numérico e
  timestamp textual timezone-aware; emitir série compacta e unresolved quando
  a evidência não bastar.
- **B — collector live.** Fica para feature própria quando endpoint, credencial,
  segurança e limites de coleta estiverem definidos; não entra por inferência.
- **C — inferência de causa/saúde.** Rejeitada: um snapshot não fornece ordem
  temporal, limiar de negócio ou causa.

## Escolha

A, porque aumenta diagnóstico determinístico e economia de contexto usando a
superfície já existente. Não cria tool, verbo ou provider call, e deixa explícito
o artefato que destrava análise temporal posterior.

## Lacunas nomeadas

- Sem `lag_observations` explícito, o analyzer não inventa tendência a partir da
  ordem do arquivo ou de um único `kafka.lag`.
- ISR abaixo de replication factor é um sinal de replicação observado; não
  prova indisponibilidade, perda de dados ou causa.
- Lag crescente é uma observação de janela curta; não prova backlog de negócio,
  SLO violado, throughput insuficiente ou causa no consumidor.

## Próximo passo

Definir facts compactos, regras com evidência suficiente, goldens positivos e
unresolved, e extensão do especialista/knowledge sem nova superfície pública.
