# Revisão operacional de Lake Formation

Use `sparkforge lakeformation architect --input architecture.json` para
produzir uma revisão offline. O JSON declara engine, runtime, formato,
operação, catálogos e evidence; facts de Terraform/PySpark entram em `facts`.
O mesmo payload pode ser enviado a `sparkforge_lakeformation_architect`.

## Leitura do resultado

- `decision`: capability e modelo FGAC/FTA.
- `review.code_and_iac`: DynamicFrame, direct S3 e configuração tardia.
- `review.access_explain`: caminho metadata/data.
- `review.authorization`: separação de catálogo, grant, credencial, S3 e KMS.
- `review.preflight`: checks por layer, sem conclusão por ausência.
- `review.root_cause`: erro, hipóteses, evidence, prova requerida e rollback.
- `review.migration`: mudanças para Glue 4→5.1 ou outra transição declarada.
- `review.performance_finops`: medidas necessárias; sem ganho inventado.

## Credential vending

Para `GetDataAccess`, `GetTemporaryCredentialsForTable` ou
`GetTemporaryCredentialsForTableV2`, validar em ordem: grant Lake Formation,
`lakeformation:GetDataAccess`, ownership/CatalogId, registered location,
application integration, filesystem, S3 e KMS. Um `403` não é motivo suficiente
para adicionar permissão S3 ampla.

## Cross-account

Validar produtor e consumidor separadamente: RAM share/association/invitation,
versão cross-account, resource link, nome do recurso, CatalogId, grants,
`IAMAllowedPrincipals`, hybrid opt-in, storage e criptografia. `glue.id` e
`glue.account-id` são propriedades independentes.

## MERGE e migração

Capability, formato, runtime e autorização são dimensões distintas. Para
Glue 4→5.1 revalidar DynamicFrame, DataFrame/Spark SQL, bookmarks, pushdown,
catálogo Iceberg, RAM e credential path. Execute plano de teste positivo e
negativo antes de promover. Rollback: restaurar runtime/configuração anterior;
o analyzer não altera AWS.

## Rollback e limites

Reverta a alteração de código/configuração que motivou a análise. Não conceda
`SUPER`, `Action: "*"` ou `Resource: "*"` sem prova e aprovação do dono. O
verbo é read-only e não substitui `collect lakeformation`, `collect iam-access`,
CloudTrail, logs Glue/Spark ou benchmark.
