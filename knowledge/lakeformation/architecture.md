# Arquitetura version-aware de Lake Formation

Este documento descreve o contrato offline usado por
`sparkforge lakeformation architect` e por
`sparkforge_lakeformation_architect`. Ele não substitui facts coletados nem
simula uma chamada AWS: organiza declarações e evidências disponíveis, preserva
lacunas e recusa recomendações genéricas de S3.

## Dimensões que não podem ser colapsadas

Uma arquitetura precisa declarar, quando conhecidos:

- engine e runtime: Glue, EMR on EC2 ou EMR Serverless, com release exata;
- modelo de acesso: FGAC ou Full Table Access (FTA); `both` é conflito;
- formato e operação separadamente: Iceberg/Parquet/Hive/Delta e read/write/
  merge/DDL;
- `job_account_id`, `local_account_id`, `source_account_id` e
  `target_account_id`;
- para cada catálogo: nome, `owner_account_id`, `glue_id` e
  `glue_account_id`.

`glue.id` e `glue.account-id` são propriedades distintas. Divergência entre
elas sai como `glue_id_account_id_diverge`; ausência não vira inferência de
ownership. O resultado publica `required_verification` em vez de preencher o
valor ausente.

## Capability matrix

[`capability-matrix.yaml`](capability-matrix.yaml) é a fonte versionada das
células consultadas pelo motor. Cada célula combina engine, release, modelo,
formato, operação e, quando aplicável, API. `supported`, `limited`,
`read_only`, `version_dependent`, `not_supported` e `unknown` são estados
intencionais; `unknown` significa que a fonte não permite decidir, não que o
recurso foi provado incompatível.

## Fontes

Fontes oficiais consultadas em 2026-09-30:

- [Glue FTA](https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html)
- [Modelos de acesso do Glue](https://docs.aws.amazon.com/glue/latest/dg/lake-formation-access-control-models.html)
- [Considerações do Lake Formation no Glue](https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html)
- [EMR EC2 com Lake Formation](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-lf-enable.html)
- [EMR EC2 FTA](https://docs.aws.amazon.com/emr/latest/ManagementGuide/lake-formation-unfiltered-ec2-access.html)
- [EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/lake-formation-section.html)
- [Compartilhamento cross-account](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-data-sharing-lf.html)

O motor não extrapola de uma release vizinha. Glue 6.x e combinações que não
estão declaradas permanecem `unknown`/`unresolved` até uma nova fonte ser lida.

## Cross-account, credential vending e preflight

RAM share, resource link, IAM `lakeformation:GetDataAccess`, grants do Lake
Formation, localização registrada, integração da aplicação e filesystem são
evidências independentes. Um resource link presente não prova que o convite
RAM foi aceito; `allowed` em IAM não prova bucket policy, KMS key policy ou Glue
resource policy.

O preflight em FTA separa:

1. capacidade da release e formato/operação;
2. integração da aplicação e filesystem compatível;
3. `GetDataAccess` do runtime role;
4. permissão do Lake Formation para a operação, incluindo `ALL`/`SUPER` quando
   a operação de escrita exigir;
5. topologia cross-account e ownership dos catálogos.

Em Glue 5.1, a troca para S3A é material para FTA: uma configuração de
resolver de credencial dependente de EMRFS não é tratada como prova de que o
vending funcionará. Em EMR e EMR Serverless, a release e o tipo de operação
continuam obrigatórios para distinguir leitura, escrita, DDL e DML.

## Saída e estados

O motor retorna:

- `consistent`: a declaração e as evidências fornecidas não deixaram lacuna;
- `unresolved`: há capability, ownership, cross-account ou preflight que ainda
  precisa de evidência;
- `blocked`: existe conflito ou cenário explicitamente incompatível.

Cada decisão contém `observed`, `inferred`, `required_verification`, `risks` e
`rollback`. `inferred` não inventa permissões. O rollback é uma orientação
local reversível; o verbo não altera AWS.

## Golden path e anti-patterns

O golden path suportado pelo contrato é Glue 5.1 no consumidor B lendo Iceberg
catalogado na conta A por resource link/RAM e escrevendo no catálogo local B,
com FGAC, operações e ownership declarados separadamente.

Casos que falham fechado: FGAC e FTA juntos; DynamicFrame legado usado como se
fosse FGAC Spark-native em Glue 5.x; acesso cross-account a tabela governada
reduzido a `spark.read.parquet`/S3 direto; ou capability fora da matriz tratada
como suportada por analogia.

O verbo é uma decisão de arquitetura declarada. Coletas AWS continuam nos
verbos `collect lakeformation`, `collect iam-access` e
`collect glue-resource-link`; depois, fatos podem ser reavaliados pelo fluxo
normal de `fuse`/`judge`.
