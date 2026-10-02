---
name: review-event-driven-architecture
description: "Use quando houver dump de EventBridge, EventBridge Pipes, SQS ou SNS e for preciso revisar entrega, retry, DLQ, redrive e pontos cegos sem confundir configuração com prova de execução."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/event-driven-architecture.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge analyze event-driven
  - sparkforge judge
subagent: true
---

# Review Event-Driven Architecture

Esta skill analisa configuração salva. Não chama AWS e não transforma uma
regra, fila ou subscription em prova de entrega, exactly-once, replay ou
idempotência.

## Procedimento

1. Gere ou receba um dump JSON com estado, targets, retry/DLQ, redrive,
   subscriptions, origem e destino de Pipes:

```bash
sparkforge analyze event-driven \
  --path event-driven.json \
  --out event-driven.facts.json
```

2. Leia todos os `event_driven.unresolved` antes do julgamento. Campos ausentes
   não são `false` seguro; são evidência que precisa ser coletada.

3. Julgue com o catálogo:

```bash
sparkforge judge --facts event-driven.facts.json --show-skipped
```

4. Para `SF-EVENT-001`, valide poison message, maxReceiveCount, retenção,
   replay e consumer idempotente. Para `SF-EVENT-002`, confirme target, role,
   policy de invocação e métrica de execução.

## Limites

- configuração não prova que mensagem foi entregue;
- DLQ não prova que o consumer é idempotente;
- retry não prova ausência de duplicação;
- ausência de finding não prova saúde;
- nenhuma mutação live ou alteração destrutiva pertence a esta skill.

Toda recomendação mantém evidence, root cause como hipótese quando necessário,
risks, trade-offs, validation e rollback.

## Quando NÃO usar

Não use para provar entrega em produção, latência, replay ou idempotência sem
event log/métrica correspondente.

## Referência rápida

`fact_id` ancora configuração; `*.unresolved` registra o ponto cego; findings
separam observação de hipótese e exigem `validation` e `rollback`.

## Red flags

Retry configurado não prova entrega; DLQ configurada não prova recuperação; a
ausência de erro em configuração não prova saúde.

## Contrato de qualidade SparkForge (v1)

Nenhuma declaração de EventBridge, SQS ou SNS vira prova de execução sem
evidência observada e rastreável.

## Protocolo

Siga `AGENT_PROTOCOL.md`, não executa manutenção destrutiva; sobe qualquer
mutação ao operador.
