---
sdd: 1
feature: EVENT_DRIVEN_ARCHITECTURE
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Extrator offline para dumps declarados de EventBridge, Pipes, SQS e SNS, com unresolved para lacunas de entrega."
    tradeoffs:
      - "preserva evidência de configuração sem fingir prova de execução"
      - "exige snapshot ou dump produzido fora do core"
  - id: B
    summary: "Inferir entrega, replay e idempotência pela presença nominal de recursos."
    tradeoffs:
      - "saída aparentemente mais completa"
      - "confunde configuração com comportamento e cria findings sem evidência"
chosen: A
---

# EVENT_DRIVEN_ARCHITECTURE — exploração

## Problema

O prompt exige conhecimento operacional de event, command, notification,
message, stream, queue, topic e pub/sub, além de EventBridge rules/Pipes,
SQS, SNS, retry, DLQ e padrões outbox/CQRS/saga. O repositório tinha
conhecimento genérico, mas não um contrato de artefato que pudesse ser
extraído, julgado e roteado.

## Escopo desta wave

Adicionar um extractor determinístico e offline para JSON salvo. Preservar
identidade, targets, retry/DLQ, redrive, subscriptions e Pipes. Ausência de
evidência vira campo não declarado ou `event_driven.unresolved`; nenhuma
conclusão de entrega, exactly-once, replay ou idempotência será inferida.

## Perguntas respondidas

1. O analyzer chama AWS? Não; lê JSON já capturado.
2. Fila sem redrive prova perda? Não; permite finding de ausência de proteção
   declarada, sem atribuir incidente.
3. Regra habilitada sem target prova que nunca executa? Não; acusa lacuna do
   dump e orienta nova captura.
