---
name: review-glue-streaming
description: "Use quando houver dump JSON/JSONL de AWS Glue Streaming ou Real-Time Mode e for preciso validar runtime, restrições, capacidade observada e lacunas sem chamar AWS."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/glue-streaming-rtm.md
  primary_verbs:
  - sparkforge analyze glue-streaming
  - sparkforge judge
subagent: true
agent: streaming-realtime-architect
---

# Review Glue Streaming

Analise somente dumps de definição ou configuração de AWS Glue Streaming já
salvos. O analyzer é offline: não chama Glue, Kafka, Kinesis ou CloudWatch e
não transforma campo ausente em zero. Separe Glue Streaming micro-batch de
Real-Time Mode e declare o runtime observado.

## Procedimento

1. Rode `sparkforge analyze glue-streaming --path <dump.json-ou-diretorio>`.
2. Preserve `glue.streaming.unresolved` e confirme o que falta antes de julgar.
3. Rode `sparkforge judge --facts <facts.json> --show-skipped`.
4. Para RTM, confira explicitamente Glue 6.0, Scala, Kafka, stateless, output
   Update, ausência de `foreachBatch`, ausência de auto scaling e capacidade de
   partições/task slots. Não derive uma medida da quantidade de workers.
5. Correlacione com Terraform, código, métricas, checkpoint e validação
   funcional quando esses artefatos existirem. Um dump de configuração não
   prova comportamento produtivo nem causalidade.

## Limites

- Não coletar ou alterar AWS, job, worker, broker, stream ou checkpoint.
- Não declarar suporte ou incompatibilidade sem a versão/rule/fact observado.
- Não afirmar latência, custo, throughput ou ganho sem baseline comparável.
- Não declarar equivalência funcional: valide contagem, schema, chave e agregados.

## Entrega

Retorne facts, findings, unresolved, hipótese e recomendação separados. Cada
finding aponta `fact_id` e `rule_id`; cada recomendação traz evidência, risco,
trade-off, validação e rollback. Nomeie o artefato que destrava qualquer decisão
que permaneça unresolved.

## Protocolo

Siga `AGENT_PROTOCOL.md`: abra/recupere o case, consulte
`sparkforge_next_step`, valide a saída, não executa manutenção destrutiva e
sobe mutações ao operador.
