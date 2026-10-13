# Event-driven architecture — contrato offline

Este documento separa event, command, notification, message, stream, queue,
topic e pub/sub. O analyzer `analyze event-driven` lê dumps JSON já salvos de
EventBridge rules/Pipes, SQS queues e SNS topics/subscriptions; não consulta AWS.

## Evidência mínima

- EventBridge: estado, event pattern, targets, retry policy e DLQ do target.
- SQS: FIFO, visibility timeout e redrive policy/DLQ.
- SNS: tópico, subscription, protocolo, endpoint e redrive quando declarado.
- Pipes: fonte, destino, enrichment e estado.

Ausência de target, redrive, retry ou identidade vira `event_driven.unresolved`
ou deixa campo explicitamente não declarado. O motor não conclui entrega,
idempotência, exactly-once, replay ou ausência de perda a partir de configuração isolada.

## Padrões para revisar

Transactional outbox reduz a janela entre commit de negócio e publicação. CQRS
separa modelos de escrita e leitura; event sourcing preserva eventos como fonte
de estado. Sagas podem usar choreography ou orchestration. Retry sem limite,
DLQ e consumidor idempotente pode criar duplicação e poison messages; esses
atributos exigem evidência do artefato e do runbook.

## Fontes

- [Amazon EventBridge rules](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html)
- [EventBridge Pipes](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html)
- [Amazon SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
- [Amazon SNS message delivery retries](https://docs.aws.amazon.com/sns/latest/dg/sns-message-delivery-retries.html)
