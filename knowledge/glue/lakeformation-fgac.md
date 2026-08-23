# Lake Formation com controle de acesso fino (FGAC) em jobs AWS Glue

Controle de acesso fino do Lake Formation não é uma permissão que se concede e
esquece: ligá-lo num job Glue muda o que o job **pode ser**. Parte do que era
código legítimo passa a ser bloqueada, e parte da capacidade paga deixa de rodar
trabalho do usuário. Este documento está organizado por consequência prática — o
que FGAC exige, o que ele proíbe, o que ele custa em capacidade, e o recorte
próprio de Iceberg — e não pela ordem da página de origem.

Toda afirmação daqui vem de *Considerations and limitations* do AWS Glue
Developer Guide, lida em 2026-08-22. O que essa página não diz não está escrito
aqui; o que ela não cobre está no fim, marcado como a verificar.

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

- **Só session catalog.** Tabela Iceberg registrada num catálogo de nome
  arbitrário não entra; o caminho suportado é o session catalog.
- **Metadata tables reduzidas.** Uma tabela registrada expõe apenas `history`,
  `metadata_log_entries`, `snapshots`, `files`, `manifests` e `refs`. O Glue
  **esconde** `partitions`, `path` e `summaries`. Diagnóstico de layout que
  dependa de `partitions` ou `summaries` não tem esse caminho sob FGAC.
- **`register_table` e `migrate` não são suportados** — e não são suportados para
  tabela nenhuma, não só para as registradas no Lake Formation.
- **A AWS recomenda `DataFrameWriterV2`** em vez da API V1 de escrita.

## 5. A verificar

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

## Fontes

- Considerations and limitations — AWS Glue with Lake Formation fine-grained access control. https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html (retrieved 2026-08-22)
