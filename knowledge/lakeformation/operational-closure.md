# Lake Formation — operational closure

Este documento descreve a camada operacional composta por
`sparkforge lakeformation architect`. Ele não substitui facts nem coleta AWS:
recebe declarações e facts já extraídos e organiza revisão, preflight,
explain-access, root-cause e migração.

## Contrato evidence-first

`review.code_and_iac` lê apenas facts declarados (`pyspark.*`, `tf.*` e
`spark.conf_effective`). Cada item mantém `kind`, arquivo/linha e atributos.
DynamicFrame em FGAC Glue 5.x/6.x, caminho direto S3 para recurso governado e
configuração Lake Formation depois do primeiro acesso são bloqueios nomeados.
Sem linha/order observado, o resultado é `required_verification`, nunca uma
inferência de ordem.

`review.authorization` separa metadata (Glue Catalog, `CatalogId`,
database/table e grant Lake Formation) de data (localização registrada,
credential vending, S3 e KMS). `SELECT`/`DESCRIBE` não provam
`INSERT`/`DELETE`/`ALTER`/`MERGE`. `lakeformation:GetDataAccess` é IAM e não
substitui grant Lake Formation.

## Explain access e root cause

O caminho mínimo é:

```text
job → Glue Catalog → Lake Formation → RAM/resource link →
producer catalog → credential vending → S3 → KMS
```

O classificador preserva classes `catalog_routing`, `lakeformation`,
`credential_vending`, `ram`, `s3`, `kms` e `unknown`. `AccessDenied` no S3 não é
automaticamente IAM: primeiro verificar qual credential path deveria existir.
`GetTemporaryCredentialsForTable`, `GetTemporaryCredentialsForTableV2` e
`GetDataAccess` exigem prova independente de IAM, grant, ownership e registro.
Root-cause devolve sintoma, camadas, evidence, hipóteses, checks, required
proof, fix least-privilege e verification. Não produz `Action: "*"`,
`Resource: "*"` nem bypass por `spark.read.parquet`.

## Migração e matriz

Para Glue 4.0 → 5.0/5.1, o relatório separa breaking, semantic, security,
performance e cost changes. DynamicFrame/GlueContext FGAC não é convertido
cegamente em acesso S3; a revisão precisa revalidar bookmarks, pushdown,
schema, catálogo, RAM, grants e credential path.

Glue 6.0 tem células próprias. A fonte de migração documenta continuidade de
FTA e limitações de FGAC, Iceberg v3 e VARIANT; ela não autoriza copiar toda a
matriz 5.1. Divergência entre página geral de FTA e página de migração fica
`version_dependent` até resolver a fonte.

## Performance, FinOps e economia

FGAC pode envolver system/user context e FTA é caminho de tabela completa; a
saída descreve impacto condicional, não um percentual. Para afirmar custo ou
ganho são necessários runs comparáveis, duração, workers, `DPUSeconds`, base de
custo e verificação de correção. Sem isso, `measurements_required` permanece
explícito.

progressive disclosure seleciona primeiro engine/runtime/model/format/operation
e só carrega referências relevantes. Glue + Iceberg + cross-account não carrega
EMR, Hudi ou Delta sem dimensão declarada.

## Runbooks

1. **Glue 5.1 não lê Parquet cross-account:** conferir CatalogId/owner,
   resource link com mesmo nome, RAM, grant, registro e credential path.
2. **Glue 5.1 não lê Iceberg cross-account:** conferir também `GlueCatalog`,
   session catalog, `glue.id` e `glue.account-id` separadamente.
3. **Lê mas não faz MERGE:** separar capability do runtime, operação, grant,
   IAM, localização e commit Iceberg; não trocar para S3 direto.
4. **Credential vending negado:** conferir `GetDataAccess`, grant, registro,
   role da localização, catálogo e KMS; coletar log exato depois dos facts.
5. **RAM invisível ou resource link ausente:** verificar share, associação,
   convite, ownership, versão cross-account e nome do link.
6. **FTA falha:** conferir modelo exclusivo, full-table permission, filesystem,
   aplicação integrada e `GetDataAccess`.
7. **EMR FGAC/FTA:** confirmar release, filesystem, integração do produtor e
   consumidor; FGAC e FTA não coexistem na mesma aplicação.

## Fontes oficiais

- AWS Glue FGAC: https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable.html
- AWS Glue FTA: https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html
- Glue 5.1: https://docs.aws.amazon.com/glue/latest/dg/migrating-version-51.html
- Glue 6.0: https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html
- Lake Formation cross-account: https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html
- EMR Lake Formation: https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-lf-enable.html
