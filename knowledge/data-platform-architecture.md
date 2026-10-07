# Arquitetura de Plataformas de Dados

Comece por workloads e access patterns. Explicite dominios, ownership, contratos, zonas, SLAs, qualidade, seguranca, observabilidade, custo e evolucao. Registre ADRs com contexto, alternativas, consequencias, validacao e rollback.

Separe ingestao, bruto, padronizado, produtos analiticos, serving e consumo. Use S3 e formatos colunares para analitico, Iceberg para snapshots e commits, Athena para SQL, DynamoDB para chave, Neptune para traversal e Step Functions para coordenacao.

Fonte: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
