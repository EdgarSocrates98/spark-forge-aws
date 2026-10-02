---
name: review-cdc-replication
description: "Use quando houver dump local de eventos CDC, Debezium/Kafka Connect, AWS DMS ou Schema Registry e for preciso revisar chaves, posições, transações, snapshot/CDC seam, deletes, tombstones, schema history, compatibilidade, contratos e pontos cegos sem chamar serviços externos."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/cdc-replication.md
  - ../../knowledge/schema-registry-data-contracts.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge analyze cdc
  - sparkforge analyze schema-registry
  - sparkforge judge
subagent: true
---

# Review CDC Replication

Analise somente artefatos CDC, Debezium/Kafka Connect ou AWS DMS já salvos.
O fluxo é offline: não chama banco, broker, connector, DMS, Glue ou provider.
O `artifact` seleciona o vocabulário e impede misturar configuração de
Debezium com evento CDC ou tarefa DMS.

## Procedimento

1. Confirme a origem, destino, runtime e janela do caso. Se o dump não trouxer
   posição, chave, schema history ou corte snapshot/CDC, preserve o `*.unresolved`.
2. Extraia o domínio:

   ```bash
   sparkforge analyze cdc --path <dump-ou-diretorio> --artifact cdc --out .sparkforge/facts_cdc.json
   sparkforge analyze cdc --path <dump-ou-diretorio> --artifact debezium --out .sparkforge/facts_debezium.json
   sparkforge analyze cdc --path <dump-ou-diretorio> --artifact dms --out .sparkforge/facts_dms.json
   ```

3. Julgue fatos observados:

   ```bash
   sparkforge judge --facts .sparkforge/facts_cdc.json --show-skipped
   ```

   Em MCP, a extração é `sparkforge_analyze_cdc`.
   Para contrato/evolução de schema:

   ```bash
   sparkforge analyze schema-registry --path <contract.json> --out .sparkforge/facts_schema.json
   sparkforge judge --facts .sparkforge/facts_schema.json --show-skipped
   ```

   Em MCP, a extração é `sparkforge_analyze_schema_registry`.
4. Correlacione posição e chave por entidade, transação, snapshot/CDC seam,
   delete/tombstone, schema history, compatibilidade e evolução de contrato,
   table mappings, endpoints e estatísticas.
5. Valide contagem, schema, chaves e agregados como proxies declarados; eles
   não provam identidade completa do resultado.

## Limites

- Não inferir exactly-once de checkpoint, posição ou configuração.
- Não transformar ausência de evidência em ausência do comportamento.
- Não afirmar compatibilidade, ausência de perda, custo ou ganho sem medida.
- Não publicar segredos, credenciais ou endpoints sensíveis.
- Não executar alteração em banco, broker, connector, DMS ou AWS.

## Entrega

Separar facts, findings, unresolved, hipótese e recomendação. Toda
recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`,
`proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e
`rollback`. Declarar exatamente qual artefato destrava cada próxima decisão.

## Protocolo

Siga `AGENT_PROTOCOL.md`: abra/recupere o case, consulte
`sparkforge_next_step`, use `sparkforge_rules_lookup` para regra e fonte,
valide a saída, não executa manutenção destrutiva e sobe qualquer mutação ao
operador.

## Contrato de qualidade SparkForge (v1)

Facts preservam `fact_id`; `*.unresolved` nomeia lacunas; toda recomendação
declara validation, risco e rollback.

## Quando NÃO usar

Não use para produzir eventos, alterar connector, registry, banco ou broker.
Sem artefato salvo, encaminhe coleta ao operador.

## Referência rápida

Posição, chave e seam devem ser observados. Cada finding usa `fact_id`; cada
`*.unresolved` vira uma lacuna; `validation` e `rollback` são obrigatórios.

## Red flags

Snapshot concluído não prova CDC contínuo; tombstone ausente não prova delete
perdido; compatibilidade declarada não prova consumidor compatível.
