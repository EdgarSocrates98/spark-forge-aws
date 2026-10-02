<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `review-glue-streaming`

Use quando houver dump JSON/JSONL de AWS Glue Streaming ou Real-Time Mode e for preciso validar runtime, restrições, capacidade observada e lacunas sem chamar AWS.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/review-glue-streaming/SKILL.md` |
| `metadata` | {'sparkforge_contract': 'v1', 'evals': 'evals/evals.json', 'references': ['references/README.md', '../_shared/references/evidence-first.md', '../_shared/references/evaluation-contract.md', '../_shared/references/operational-safety.md', '../../knowledge/glue-streaming-rtm.md'], 'scripts': ['scripts/validate_evidence.py'], 'primary_verbs': ['sparkforge analyze glue-streaming', 'sparkforge judge']} |
| `subagent` | True |

## Procedimento (texto integral)

## Review Glue Streaming

Analise somente dumps de definição ou configuração de AWS Glue Streaming já
salvos. O analyzer é offline: não chama Glue, Kafka, Kinesis ou CloudWatch e
não transforma campo ausente em zero. Separe Glue Streaming micro-batch de
Real-Time Mode e declare o runtime observado.

### Procedimento

1. Rode `sparkforge analyze glue-streaming --path <dump.json-ou-diretorio>`.
2. Preserve `glue.streaming.unresolved` e confirme o que falta antes de julgar.
3. Rode `sparkforge judge --facts <facts.json> --show-skipped`.
4. Para RTM, confira explicitamente Glue 6.0, Scala, Kafka, stateless, output
   Update, ausência de `foreachBatch`, ausência de auto scaling e capacidade de
   partições/task slots. Não derive uma medida da quantidade de workers.
5. Correlacione com Terraform, código, métricas, checkpoint e validação
   funcional quando esses artefatos existirem. Um dump de configuração não
   prova comportamento produtivo nem causalidade.

### Limites

- Não coletar ou alterar AWS, job, worker, broker, stream ou checkpoint.
- Não declarar suporte ou incompatibilidade sem a versão/rule/fact observado.
- Não afirmar latência, custo, throughput ou ganho sem baseline comparável.
- Não declarar equivalência funcional: valide contagem, schema, chave e agregados.

### Entrega

Retorne facts, findings, unresolved, hipótese e recomendação separados. Cada
finding aponta `fact_id` e `rule_id`; cada recomendação traz evidência, risco,
trade-off, validação e rollback. Nomeie o artefato que destrava qualquer decisão
que permaneça unresolved.

### Protocolo

Siga `AGENT_PROTOCOL.md`: abra/recupere o case, consulte
`sparkforge_next_step`, valide a saída, não executa manutenção destrutiva e
sobe mutações ao operador.

### Quando NÃO usar

Não use para provisionar Glue, alterar job ou coletar CloudWatch. Sem dump
observado, a resposta deve permanecer unresolved.

### Referência rápida

Declare runtime e artefato; `fact_id` ancora cada finding; `*.unresolved` nomeia
blind spots; toda recomendação traz `validation` e `rollback`.

### Red flags

Worker count não é task capacity; RTM não é micro-batch; configuração não prova
backlog, latência ou resultado funcional.

### Contrato de qualidade SparkForge (v1)

Facts offline sustentam diagnóstico; não invente capacidade nem ganho e mantenha
risco, trade-off, validation e rollback.
