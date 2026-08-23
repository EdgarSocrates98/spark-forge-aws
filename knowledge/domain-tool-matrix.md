# Matriz de Dominios e Ferramentas

Arquitetura usa sf-data-architect; Airflow usa sf-airflow-specialist; agents usam sf-agent-builder; Iceberg, Parquet e S3 usam seus especialistas; Terraform usa sf-terraform-specialist; grafos e Neptune usam sf-graph-specialist e sf-neptune-specialist; DynamoDB e Athena usam seus especialistas.

Todo handoff contem goal, facts, decisions, uncertainties, artifacts, risks, validation, rollback e next_action. Comece com coleta barata e deterministica e escale somente quando risco e incerteza justificarem.
