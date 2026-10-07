# Grafos, Neptune, DynamoDB e Athena

Use grafo quando relacionamentos, caminhos, vizinhancas ou comunidades forem centrais. Neptune exige escolha de engine, schema, consultas limitadas, bulk load, replicas, backups e IAM. DynamoDB deve ser modelado por access patterns, PK, SK, GSIs, capacidade, hot keys, Streams e conditional writes.

O conector Athena-DynamoDB usa SQL, nao suporta INSERT INTO, pode fazer spill em S3 e aceita predicate pushdown e LIMIT; scans podem consumir RCUs. Controle bytes scanned, particoes, Parquet, workgroups e custo.

Fonte: https://docs.aws.amazon.com/athena/latest/ug/connectors-dynamodb.html
