# Lake Formation com controle de acesso fino (FGAC) em jobs AWS Glue

Controle de acesso fino do Lake Formation não é uma permissão que se concede e
esquece: ligá-lo num job Glue muda o que o job **pode ser**. Parte do que era
código legítimo passa a ser bloqueada, e parte da capacidade paga deixa de rodar
trabalho do usuário. Este documento está organizado por consequência prática — o
que FGAC exige, o que ele proíbe, o que ele custa em capacidade, e o recorte
próprio de Iceberg — e não pela ordem da página de origem.

As afirmações daqui vêm de cinco páginas do AWS Glue Developer Guide, e **cada
seção nomeia a sua**. A coleta original é de 2026-08-22, sobre *Considerations
and limitations* apenas; as seções 0, 5 e 6 entraram em 2026-09-09, com as
páginas de FGAC, de Full Table Access e as duas de migração. O que essas páginas
não dizem não está escrito aqui; o que elas não cobrem está no fim, marcado como
a verificar.

## 0. O eixo de versão, e por que ele vem antes de tudo

A página de *Considerations and limitations* **não tem eixo de versão**: ela fala
de "AWS Glue com Lake Formation" sem dizer de qual runtime. Ler as seções abaixo
sem esta tabela produz o erro que mais engana nesta área — aplicar a um Glue 5.1
uma limitação que era do 5.0, ou o contrário.

| | Glue 4.0 | Glue 5.0 | Glue 5.1 |
|---|---|---|---|
| Spark | 3.3.0-amzn-1 | 3.5.4 | 3.5.6 |
| Iceberg | 1.0.0 | 1.7.1 | 1.10.0 |
| Filesystem S3 default | EMRFS | EMRFS | **S3A** |
| FGAC via `GlueContext`/DynamicFrame | suportado | **removido** | removido |
| FGAC Spark-native (leitura) | não existe | suportado | suportado |
| FGAC Spark-native (escrita de dado) | não existe | **não suportado** | **suportado** |
| FGAC DDL/DML (CREATE/ALTER/DELETE/DROP) | — | não declarado | suportado |
| FTA Spark-native | não existe | Hive e Iceberg | + Hudi e Delta |
| FTA via `GlueContext`/DynamicFrame | suportado | só tabela não-OTF | só tabela não-OTF |
| FTA DDL/DML (CREATE/ALTER/DELETE/UPDATE/MERGE INTO) | — | suportado | suportado |
| FTA com biblioteca custom, UDF e RDD | — | suportado | suportado |

As três linhas que decidem, com a citação:

**Glue 5.0 removeu o modelo do 4.0.** *"`GlueContext`-based table-level access
control with AWS Lake Formation permissions supported in Glue 4.0 or before is
not supported in Glue 5.0."* Um job de 4.0 que lia tabela protegida por
`create_dynamic_frame.from_catalog` **não tem tradução direta** para FGAC no 5.x:
o caminho é migrar para DataFrame do Spark.

**Glue 5.0 não escrevia sob FGAC.** A página de migração para o 5.0 diz, nas
considerações do Spark-native FGAC: *"Currently data writes are not supported"* e
*"Writing into Iceberg through `GlueContext` using Lake Formation requires use of
IAM access control instead"*.

**Glue 5.1 passou a escrever.** A página de migração para o 5.1 declara
*"Spark native fine-grained access control (FGAC) support using AWS Lake
Formation - DDL/DML operations (like CREATE, ALTER, DELETE, DROP) with fine
grained access control for Apache Hive, Apache Iceberg and Delta Lake tables
registered in AWS Lake Formation"*, e no bloco do Iceberg: *"Support
Spark-native FGAC writes on AWS Lake Formation registered tables."*

**Isso NÃO diz que a permissão do Lake Formation passou a autorizar a escrita.**
Ver a seção 6.

**As duas últimas linhas são uma ASSIMETRIA, e ela é citável dos dois lados**
(coletado em 2026-09-10). A página de Full Table Access **enumera**:
*"This capability enables Data Manipulation Language (DML) operations including
CREATE, ALTER, DELETE, UPDATE, and MERGE INTO statements on Apache Hive and
Iceberg tables."* A de migração para o 5.1, do lado FGAC, diz
*"DDL/DML operations (**like** CREATE, ALTER, DELETE, DROP)"* — sem `MERGE INTO`,
sem `UPDATE`, e com um "like" que torna a lista **ilustrativa e não exaustiva**.

Portanto: `MERGE INTO` sob FTA é suportado **por escrito**; sob FGAC ele **não é
nomeado em lugar nenhum**, e concluir daí que não funciona seria ler uma lista de
exemplos como fechada. A pergunta continua aberta, e é assim que a matriz a
publica.

**A linha da biblioteca custom fecha o outro lado do tradeoff de `SF-LF-001`.**
Aquela regra acusa `--extra-jars` sob FGAC — que a AWS bloqueia — e propõe, como
uma das saídas, trocar de modelo de acesso. O benefício dessa troca era afirmado
sem citação até aqui; a página de FTA a dá: *"supports Spark capabilities
including Resilient Distributed Datasets (RDDs), custom libraries, and User
Defined Functions (UDFs) with AWS Lake Formation tables."*

**A quarta linha, e ela é breaking change de filesystem:** *"S3A filesystem has
replaced EMRFS as the default S3 connector"* no Glue 5.1. A consequência para
esta área está na seção 5.

## 1. O que FGAC exige

**O parâmetro de job.** Para habilitar controle de acesso fino num job Glue,
passa-se o job parameter `--enable-lakeformation-fine-grained-access`. Não é uma
propriedade do recurso Terraform nem uma configuração de sessão Spark: é
argumento de job, e vive junto do resto dos `default_arguments`.

**Job Spark, e só.** *"You can only use Lake Formation with Spark jobs."* Um job
Python shell não entra nesta conversa.

**Formato de tabela Hive ou Iceberg.** O suporte a FGAC via Lake Formation existe
apenas para tabelas Apache Hive e Apache Iceberg. Os formatos Hive incluem
Parquet, ORC e CSV.

**Uma única sessão Spark no job inteiro.** *"AWS Glue with Lake Formation only
supports a single Spark session throughout a job."* Código que encerra a sessão e
abre outra — padrão comum para "resetar" configuração no meio de um pipeline — não
é suportado sob FGAC.

**Cross-account só por resource link, com nome idêntico.** Consulta a tabela de
outra conta só é suportada quando compartilhada por resource link, e o resource
link **precisa ter o mesmo nome do recurso na conta de origem**. Um link com nome
próprio, ainda que aponte para o lugar certo, está fora do que a AWS declara
suportado.

Desde 2026-09-10 esta afirmação tem **fact medido** e não vive mais só nesta
página: `sparkforge collect glue-resource-link` lê o objeto na conta consumidora
com `glue:GetTable` (ou `glue:GetDatabase`), guarda os dois nomes verbatim, e
`glue.resource_link.attrs.name_matches_source` os compara. `SF-XACC-002` julga
sobre isso — e o achado é sobre o **limite de suporte declarado**, não sobre uma
negação observada: um link com nome próprio pode responder hoje, e o que a AWS
não declara é que ele continue respondendo. A comparação não é a mesma nos dois
tipos: link de tabela compara contra `TargetTable.Name`, link de banco contra
`TargetDatabase.DatabaseName`, que não tem campo `Name`.

**Mínimo de 4 workers.** *"Jobs with FGAC require a minimum of 4 workers: one
user driver, one system driver, one system executor, and one standby user
executor."* É o dobro do mínimo de 2 de um job Glue comum, e é fronteira dura:
não é recomendação de dimensionamento, é o piso da alocação descrita na seção 3.

**A configuração precisa existir ANTES da sessão.** *"Specifying it later using
the calls `SparkSession.builder().conf("").get()` or
`SparkSession.builder().conf("").create()` will not be enough. This is a change
from the AWS Glue 4.0 behavior."* Configuração de catálogo aplicada com
`spark.conf.set(...)` depois de a sessão existir — padrão herdado de job 4.0 —
não é lida pelo caminho de FGAC, e o job segue rodando com o catálogo que ele
tinha.

**Permissão do Lake Formation não substitui permissão de IAM na API.**
*"Although you might have the Lake Formation permission to access a table in the
Data Catalog (SELECT), your operation fails if you don't have the IAM permission
on the `glue:Get*` API operation."* São dois planos de autorização, e falhar em
qualquer um derruba a operação. A policy de exemplo da AWS concede `glue:Get*`,
`glue:Create*`, `glue:Update*` e `lakeformation:GetDataAccess`.

## 2. O que FGAC proíbe

Duas listas, e a distinção entre elas importa. A primeira é de funcionalidades
não suportadas. A segunda é do que o Glue **bloqueia** ativamente, e o motivo
declarado é preservar o isolamento completo do system driver — não é uma lacuna
de roadmap, é uma fronteira de segurança.

**Não suportado:**

- Resilient distributed datasets (RDD)
- Spark streaming
- Escrita usando permissões concedidas pelo Lake Formation
- Controle de acesso para colunas aninhadas

**Bloqueado, para não minar o isolamento do system driver:**

- UDTs, HiveUDFs, e qualquer função definida pelo usuário que envolva classes
  customizadas
- Data sources customizados
- Fornecimento de JARs adicionais para extensão do Spark, conector ou metastore
- O comando `ANALYZE TABLE`

O item dos JARs é o que mais colide com configuração existente: `--extra-jars` é
exatamente o mecanismo de "supply of additional jars", e um job que declara os dois
ao mesmo tempo está pedindo duas coisas que a AWS declara incompatíveis. O de
streaming é da mesma natureza: `gluestreaming` mais o parâmetro de FGAC é a
combinação que a lista de não suportados nomeia.

**Escrita continua acontecendo — por IAM, não por Lake Formation.** *"Writing to a
Lake Formation table uses IAM permission rather than Lake Formation granted
permissions. If your job runtime role has the necessary S3 permissions, you can
use it to run write operations."* É a distinção que mais engana no desenho: ligar
FGAC **não** faz a escrita passar a respeitar as permissões concedidas no Lake
Formation. Quem escreve é o runtime role do job, com as permissões S3 dele. Um
modelo de governança que assuma "FGAC cobre leitura e escrita" está errado sobre
a metade da escrita.

**Leitura de localização registrada passa pelas credenciais do Lake Formation.**
*"If you registered a table location with Lake Formation, the data access path
goes through the Lake Formation stored credentials regardless of the IAM
permission for the AWS Glue job runtime role."* A palavra que decide é
*regardless*: conceder ao runtime role a permissão S3 que falta **não** contorna o
caminho de acesso, porque o caminho não é o do role.

## 3. O que FGAC muda em capacidade

Sob FGAC o job deixa de ter um driver e N executores. A alocação passa a ter
quatro papéis: um **system driver**, **system executors**, um **user driver** e,
opcionalmente, **user executors** — estes últimos exigidos quando o job tem UDFs
ou usa `spark.createDataFrame`.

O exemplo da própria AWS, com **20 workers**:

| Papel | Workers |
|---|---:|
| user driver | 1 |
| system driver | 1 |
| user executors | 2 (10% dos 18 restantes) |
| system executors | até 16 |

A leitura prática: de 20 workers pagos, 2 são drivers e 2 ficam reservados para o
lado do usuário. A proporção reservada para user executors é ajustável por
`--conf spark.dynamicAllocation.maxExecutorsRatio`.

Consequência para dimensionamento: **contagem de workers sob FGAC não é comparável
com a contagem do mesmo job sem FGAC.** Comparar runtime antes e depois de ligar
FGAC sem levar a realocação em conta atribui ao controle de acesso uma lentidão
que é, em parte, capacidade que mudou de papel.

## 4. O recorte de Iceberg sob FGAC

Iceberg é suportado sob FGAC, mas com um recorte próprio que não vale para Hive:

- **Só session catalog.** *"You can only use Apache Iceberg with session catalog
  and not arbitrarily named catalogs."* Tabela Iceberg registrada num catálogo de
  nome arbitrário não entra. O nome do session catalog em Spark é
  `spark_catalog`, e a configuração que a AWS publica para rodar Iceberg sob
  FGAC é literalmente esta:

  ```
  spark.sql.catalog.spark_catalog=org.apache.iceberg.spark.SparkSessionCatalog
  spark.sql.catalog.spark_catalog.warehouse=<S3_DATA_LOCATION>
  spark.sql.catalog.spark_catalog.glue.account-id=<ACCOUNT_ID>
  spark.sql.catalog.spark_catalog.client.region=<REGION>
  spark.sql.catalog.spark_catalog.glue.endpoint=https://glue.<REGION>.amazonaws.com
  ```

  Um job que declara `spark.sql.catalog.glue_catalog=...` — padrão herdado de
  Glue 4.0, e o mais comum de todos — está fora desse recorte. **Isto vale para
  FGAC e não vale para FTA:** a própria AWS publica exemplo de FTA com
  `glue_catalog`, e a restrição de nome não aparece na página de FTA.
- **Metadata tables reduzidas.** Uma tabela registrada expõe apenas `history`,
  `metadata_log_entries`, `snapshots`, `files`, `manifests` e `refs`. O Glue
  **esconde** `partitions`, `path` e `summaries`. Diagnóstico de layout que
  dependa de `partitions` ou `summaries` não tem esse caminho sob FGAC.
- **`register_table` e `migrate` não são suportados** — e não são suportados para
  tabela nenhuma, não só para as registradas no Lake Formation.
- **A AWS recomenda `DataFrameWriterV2`** em vez da API V1 de escrita.

## 5. Full Table Access (FTA) — o outro modelo, e o que ele quebra no Glue 5.1

FGAC e FTA não são graus do mesmo controle; são dois modelos, e a AWS proíbe
os dois no mesmo job: *"Only one AWS Lake Formation permission method can be
enabled for a given AWS Glue job. A job cannot simultaneously run Full Table
Access (FTA) and Fine-Grained Access Control (FGAC) at the same time."*

**A diferença que decide não é granularidade — é QUEM vende a credencial.** Sob
FTA, *"AWS Lake Formation credentials are used to read/write Amazon S3 data for
AWS Lake Formation registered tables, while the job's runtime role credentials
will be used to read/write tables not registered with AWS Lake Formation."* Isto
é o oposto do FGAC, onde a escrita é do runtime role (seção 2). É por isso que
"trocar de modelo" muda o resultado de uma escrita que não muda de código.

**O que FTA exige, e a lista não é só de permissão:**

- na conta: *application integration for full table access* — permitir que query
  engines de terceiro acessem o dado sem a validação de session tag do IAM;
- no IAM do runtime role: `lakeformation:GetDataAccess`;
- no Lake Formation: `SELECT` para ler; **`ALL` para escrever ou apagar**;
  `DESCRIBE`, `ALTER`, `DROP` conforme a interação com o catálogo. A frase é
  literal: *"AWS Glue Spark jobs that write/delete data in Amazon S3 require AWS
  Lake Formation ALL permission."* Um grant de `SELECT` + `DESCRIBE` — que basta
  para ler — **não autoriza escrita sob FTA**;
- no Spark: `spark.sql.catalog.<catalog>.glue.lakeformation-enabled=true`, mais
  `spark.hadoop.fs.s3.credentialsResolverClass=com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver`
  e o par `useDirectoryHeaderAsFolderObject` / `folderObject.autoAction.disabled`.

**E aqui está a armadilha do Glue 5.1, que é de filesystem e não de permissão.**
A página de FTA declara: *"Full Table Access works exclusively with EMR
Filesystem (EMRFS). S3A filesystem is not compatible."* A página de migração para
o 5.1 declara: *"S3A filesystem has replaced EMRFS as the default S3 connector."*

As duas juntas dizem que **FTA num Glue 5.1 de configuração default não
funciona**. Pior que não funcionar: `fs.s3.credentialsResolverClass` é chave de
EMRFS, e sob S3A ela é **ignorada sem erro**. A credencial do Lake Formation
nunca é pedida, o acesso cai no runtime role, e o `AccessDenied` que sai disso
parece problema de Lake Formation quando é de filesystem. Restaurar EMRFS exige
as três chaves:

```
spark.hadoop.fs.s3.impl=com.amazon.ws.emr.hadoop.fs.EmrFileSystem
spark.hadoop.fs.s3n.impl=com.amazon.ws.emr.hadoop.fs.EmrFileSystem
spark.hadoop.fs.AbstractFileSystem.s3.impl=org.apache.hadoop.fs.s3.EMRFSDelegate
```

**Outros limites de FTA:** não suporta Spark Streaming; job que referencia tabela
com regra de FGAC ou Glue Data Catalog View **falha**; e tabela Hive criada por
job sem FTA e sem nenhuma linha inserida quebra leitura e escrita posteriores
com FTA, porque o Glue sem FTA cria a pasta com sufixo `$folder$` e *"AWS Lake
Formation credentials do not allow reading table folders with `$folder$`
suffix"*.

## 6. Conflito declarado: escrita em tabela registrada sob FGAC

Quatro frases da documentação atual, lidas em 2026-09-09. **Elas não fecham, e
este documento não escolhe uma.**

| | Página | Frase |
|---|---|---|
| A | migração 5.1 | *"Support Spark-native FGAC writes on AWS Lake Formation registered tables."* |
| B | FGAC (tabela de operações) | DDL e DML INSERT/UPDATE/DELETE: *"With IAM permissions only"* |
| C | considerations | não suportado: *"Write with Lake Formation granted permissions"* |
| D | considerations | *"If you registered a table location with Lake Formation, the data access path goes through the Lake Formation stored credentials **regardless** of the IAM permission for the AWS Glue job runtime role."* |

**A, B e C fecham entre si** sob uma leitura só: a operação de escrita passou a
rodar no 5.1 (A), e quem a autoriza é o IAM do runtime role (B), porque grant do
Lake Formation não autoriza escrita (C). É a mesma coisa que a seção 2 já dizia.

**C e D não fecham.** D afirma que, para localização **registrada**, o caminho de
dado usa a credencial armazenada do Lake Formation *independentemente* do IAM do
role — e C afirma que o grant do Lake Formation não autoriza escrita. Para uma
tabela registrada, a escrita fica sem caminho declarado: o do role não é usado
(D), e o do Lake Formation não autoriza (C). A frase que parece resolver —
*"If your job runtime role has the necessary S3 permissions, you can use it to
run write operations"* — é a mesma que D contradiz para o caso registrado.

**Consequência para o diagnóstico:** um job FGAC que lê tabela protegida e falha
ao escrever em tabela **registrada** está numa combinação que a documentação não
resolve. As saídas que a própria documentação sustenta são três, e todas mudam o
desenho em vez de mudar a API de escrita:

1. o alvo **não** ser registrado no Lake Formation — aí a escrita é do runtime
   role, e o que resta é `s3:PutObject`, `s3:DeleteObject` e KMS. As ações S3 vêm
   da página de permissões mínimas de job ETL, que não separa append de overwrite:
   *"Data targets require s3:ListBucket, s3:PutObject, and s3:DeleteObject
   permissions."* (`s3:ListBucket` é ação de bucket); KMS, quando o alvo usa
   SSE-KMS: *"The job role needs the kms:ReEncrypt, kms:GenerateDataKey, and
   kms:DescribeKey permissions."*, mais `kms:Decrypt`;
2. trocar o job para **FTA** — aí quem escreve é a credencial do Lake Formation,
   com `ALL` no grant, e valem os requisitos da seção 5, EMRFS incluído;
3. **separar** leitura e escrita em dois jobs, porque FGAC e FTA não coexistem
   num job só.

Nenhuma delas é "trocar `writeTo` por `INSERT INTO`": a API de escrita não é o
caminho de autorização, e mudá-la não muda nem A, nem B, nem C, nem D.

## 7. A verificar

O que a fonte desta coleta não afirma, e por isso não está escrito acima:

- A partir de qual versão de Glue o parâmetro `--enable-lakeformation-fine-grained-access`
  passou a existir não é declarado nesta página. As regras `SF-LF-*` guardam por
  `glue: ">=5.0"`; confirmar contra a página de release notes antes de citar a
  fronteira como fato.
- O comportamento sob `--enable-auto-scaling` — se a divisão de 10% para user
  executors é calculada sobre `MaxCapacity` ou sobre a capacidade corrente — não
  é coberto pela fonte. A verificar.
- Se a lista de metadata tables escondidas muda com a versão do Iceberg
  empacotada pelo runtime não é declarado. A verificar.

- Se a escrita sob FGAC em tabela **registrada** tem caminho suportado é
  exatamente o que a seção 6 mede como não declarado. A verificar contra uma
  execução real, ou contra uma revisão futura das duas páginas.
- Se `spark.sql.catalog.spark_catalog.glue.lakeformation-enabled` tem efeito sob
  FGAC — a chave aparece na página de FTA e não na de FGAC — não é declarado.
  A verificar.
- Se o Glue 5.1 mudou a lista de operações da tabela "With IAM permissions only"
  da página de FGAC não é declarado: a página não tem eixo de versão, e a de
  migração do 5.1 não a reescreve.

## Fontes

- Considerations and limitations — AWS Glue with Lake Formation fine-grained access control. https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html (retrieved 2026-08-22, relida 2026-09-09)
- Using AWS Glue with AWS Lake Formation for fine-grained access control. https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable.html (retrieved 2026-09-09)
- Using AWS Glue with AWS Lake Formation for Full Table Access. https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html (retrieved 2026-09-09)
- Migrating AWS Glue for Spark jobs to AWS Glue version 5.0. https://docs.aws.amazon.com/glue/latest/dg/migrating-version-50.html (retrieved 2026-09-09)
- Migrating AWS Glue for Spark jobs to AWS Glue version 5.1. https://docs.aws.amazon.com/glue/latest/dg/migrating-version-51.html (retrieved 2026-09-09)
- Troubleshooting — AWS Glue with Lake Formation. https://docs.aws.amazon.com/glue/latest/dg/security-lf-troubleshooting.html (retrieved 2026-09-09)
- Review IAM permissions needed for ETL jobs — AWS Glue. https://docs.aws.amazon.com/glue/latest/dg/getting-started-min-privs-job.html (retrieved 2026-09-25)
