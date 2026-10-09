# CDC, Debezium e AWS DMS — contrato evidence-first

## Escopo

Este documento cobre raciocínio sobre mudança de dados, não implementação de
conector de banco. O artefato de CDC precisa separar snapshot inicial, CDC,
operação, chave, posição no log, transação, replay, duplicidade, restart,
tombstone, heartbeat e DDL. Ausência de posição, chave, schema history,
endpoint, mapping ou corte snapshot→CDC vira `*.unresolved`.

## Debezium/Kafka Connect

Um dump de configuração deve preservar `connector.class`, banco, tabelas
incluídas/excluídas, `snapshot.mode`, heartbeat, transforms/SMTs, topic prefix,
schema history, delete/tombstone, converters e error handling. Status de
connector/task é artefato separado de configuração. Presença de offset ou
schema history não prova exactly-once end-to-end; é necessário correlacionar
posição, transação, aplicação no destino e resultado.

Fontes oficiais: [configuração e conectores Debezium](https://debezium.io/documentation/reference/stable/connectors/),
[PostgreSQL connector](https://debezium.io/documentation/reference/stable/connectors/postgresql.html),
[storage de schema history](https://debezium.io/documentation/reference/stable/configuration/storage.html).

## AWS DMS

Um task DMS tem fases de Full Load, aplicação de mudanças em cache e CDC. A
definição deve carregar tipo de migração, endpoints, replication instance,
table mappings, settings, validação, recovery e destino. Full Load + CDC exige
um corte observável entre carga e posição de log; a modalidade sozinha não
prova que o seam é seguro. DMS não oferece SLA de latência CDC: latência depende
de carga, rede, recursos da replication instance, capacidade do destino e dados.

Fontes oficiais: [tasks DMS](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.html),
[CDC](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html),
[componentes e table mappings](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Introduction.Components.html),
[troubleshooting](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Troubleshooting.html),
[target Kafka/MSK](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.Kafka.html).

## Regras do produto

`SF-CDC-*`, `SF-DEBEZIUM-*` e `SF-DMS-*` julgam somente fatos observados. O
analyzer é offline; `collect *` futuro pode produzir dumps read-only, mas não é
necessário para reextrair fixtures. A validação funcional precisa comparar
contagem, schema, chaves e valores; nenhum desses proxies prova equivalência
completa.
