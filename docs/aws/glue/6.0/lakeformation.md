# Lake Formation com controle de acesso fino (FGAC)

Conhecimento completo — o que FGAC exige, o que ele proíbe, o que ele custa em capacidade e o
recorte próprio de Iceberg — em
[`../../../../knowledge/glue/lakeformation-fgac.md`](../../../../knowledge/glue/lakeformation-fgac.md).
Este documento não repete as tabelas de lá; ele diz o que o SparkForge faz com elas.

Ligar FGAC num job Glue não é conceder uma permissão e esquecer: muda **o que o job pode
ser**. Parte do que era código legítimo passa a ser bloqueada, e parte da capacidade paga
deixa de rodar trabalho do usuário.

## A área `SF-LF`

`rules/catalog/lakeformation.yaml` declara a área **`SF-LF`**, com seis
incompatibilidades **declaradas pela AWS** — nenhuma inferida:

| Regra | O que ela acusa | Escopo |
|---|---|---|
| `SF-LF-001` | JAR adicional declarado num job com FGAC habilitado | `glue >=5.0` |
| `SF-LF-002` | FGAC habilitado num job de streaming | `glue >=5.0` |
| `SF-LF-003` | catálogo Iceberg de nome arbitrário sob FGAC | `glue >=5.0` |
| `SF-LF-004` | resolver de credencial do Lake Formation sem EMRFS restaurado | `glue >=5.1` |
| `SF-LF-005` | FGAC e Full Table Access declarados no mesmo job | `glue >=5.0` |
| `SF-LF-006` | FGAC com `number_of_workers` abaixo de 4 | `glue >=5.0` |

As duas primeiras nascem da mesma fronteira: o Glue **bloqueia** fornecimento de JAR
adicional para preservar o isolamento completo do system driver, e streaming está na lista de
não suportados. Um job que declara as duas coisas ao mesmo tempo está pedindo duas coisas que
a AWS declara incompatíveis.

A terceira é a restrição de **session catalog**: sob FGAC, Iceberg só é suportado no
`spark_catalog`, e não num catálogo de nome arbitrário. É a configuração herdada de Glue 4.0
mais comum de todas, e ela continua correta fora de FGAC — a própria AWS publica exemplo de
Full Table Access com `glue_catalog`.

**A quarta não é de Lake Formation: é de FILESYSTEM.** Full Table Access só funciona com
EMRFS, e o Glue 5.1 trocou o conector S3 default para S3A. `fs.s3.credentialsResolverClass` é
chave de EMRFS, e sob S3A ela é **ignorada sem erro** — a credencial do Lake Formation nunca
é pedida, o acesso cai no runtime role, e o `AccessDenied` resultante parece problema de
governança. Num Glue 5.0 a mesma configuração está correta, e é por isso que o escopo dela é
`>=5.1`.

### O modelo de acesso virou fact

`sparkforge/facts/lakeformation.py` deriva `lakeformation.access_model`,
`lakeformation.iceberg_catalog`, `lakeformation.filesystem`, `lakeformation.fta_declared` e
`lakeformation.unresolved` sobre
a união dos facts, sem ler artefato. Ele existe porque o DSL de regra compara **igualdade**, e
o nome do catálogo Iceberg mora **dentro** da chave de configuração
(`spark.sql.catalog.<nome>`) — o predicado teve de ser derivado num fact para a regra poder
compará-lo.

`lakeformation.unresolved` nomeia a lacuna que fecha esta área: grant do Lake Formation,
policy do runtime role e registro da localização S3 não entram em artefato nenhum que este
motor colete.

### A exceção que o job lançou

Cinco regras da área `SF-ERR` julgam falha de Lake Formation a partir do log:

| Regra | Assinatura | Companheiro |
|---|---|---|
| `SF-ERR-006` | `Insufficient Lake Formation permission(s) on` | `tf.spark_conf` |
| `SF-ERR-014` | `GetTemporaryGlueTableCredentials` | `lakeformation.access_model` |
| `SF-ERR-015` | `lakeformation:GetDataAccess` | `lakeformation.filesystem` |
| `SF-ERR-016` | `glue:GetTable` | `lakeformation.access_model` |
| `SF-ERR-017` | `Security validation exception` | `lakeformation.access_model` |

**A procedência do texto é declarada**: a página de troubleshooting do AWS Glue não publica
string de erro literal — publica título de sintoma. Três das quatro novas casam por **nome de
ação IAM ou de API**, que é a parte que a AWS publica.

O sinal de FGAC é o job parameter `--enable-lakeformation-fine-grained-access`. Não é
propriedade do recurso Terraform nem configuração de sessão Spark: é argumento de job, e vive
junto do resto dos `default_arguments`.

## Três coisas que o desenho costuma errar

**Escrita não passa pelo Lake Formation.** Escrever numa tabela Lake Formation usa permissão
**IAM**, não as permissões concedidas no Lake Formation. Quem escreve é o runtime role do
job, com as permissões S3 dele. Um modelo de governança que assuma "FGAC cobre leitura e
escrita" está errado sobre a metade da escrita.

> **Eixo de versão, e ele muda esta frase.** O Glue 5.0 declarava
> *"Currently data writes are not supported"* para Spark-native FGAC; o Glue 5.1 declara
> suporte a *"Spark-native FGAC writes on AWS Lake Formation registered tables"*. Isso **não**
> significa que o grant do Lake Formation passou a autorizar a escrita — a operação passou a
> rodar, e quem a autoriza continua sendo o IAM. Para tabela **registrada**, as duas frases
> acima colidem, e o conflito está declarado com as quatro fontes na §6 do documento de
> conhecimento. O SparkForge não escolhe um lado.

**Leitura de localização registrada não é contornável por IAM.** Se a localização da tabela
foi registrada no Lake Formation, o caminho de acesso ao dado passa pelas credenciais
armazenadas no Lake Formation **independentemente** da permissão IAM do runtime role.
Conceder ao role a permissão S3 que falta não abre o caminho, porque o caminho não é o dele.

**Contagem de worker sob FGAC não é comparável com a do mesmo job sem FGAC.** Sob FGAC a
alocação deixa de ser um driver e N executores e passa a ter quatro papéis — system driver,
system executors, user driver e, quando o job tem UDF ou usa `createDataFrame`, user
executors. O exemplo numérico da AWS está no documento de conhecimento e não é repetido aqui.
A consequência para dimensionamento é que comparar runtime antes e depois de ligar FGAC, sem
levar a realocação em conta, atribui ao controle de acesso uma lentidão que é, em parte,
capacidade que mudou de papel.

## O recorte de Iceberg

Iceberg é suportado sob FGAC, com restrições que não valem para Hive: só session catalog,
conjunto reduzido de metadata tables (o Glue esconde algumas), `register_table` e `migrate`
não suportados, e a AWS recomendando a API V2 de escrita. Diagnóstico de layout que dependa
de uma metadata table escondida **não tem esse caminho** sob FGAC — e isso é um limite da
ferramenta neste cenário, não uma falha do diagnóstico.

Há ainda a interação com a spec v3: FGAC **não é suportado com colunas VARIANT**. É escolha
entre VARIANT e granularidade de acesso, não as duas — ver [`iceberg.md`](iceberg.md).

## Onde o extrator é cego

Duas cegueiras medidas do extrator de Terraform atingem `SF-LF-001` diretamente, e o sintoma
das duas é **silêncio**:

- **`non_overridable_arguments` é ignorado inteiro.** Um `aws_glue_job` que forneça argumento
  por esse bloco é invisível para toda regra que lê `default_arguments`.
- **Valor com interpolação vira `tf.unresolved`, não `tf.attribute`.** Uma regra cuja
  condição é conjunção plana fica calada quando o atributo que ela procura foi interpolado.

As duas estão registradas em
[`../../../gates-por-mudanca.md`](../../../gates-por-mudanca.md), seção *Pontos cegos medidos
do extrator de Terraform*, porque uma regra nova que leia `default_arguments` as herda sem
perceber.

## O que não existe

Não existe matriz por **operação** (`SELECT`, `INSERT`, `MERGE`, `ALTER`) cruzada com conta:
a fonte enumera limitação, não operação, e preencher célula por operação exigiria inferir. A
distinção nominal entre permissão de catálogo, Lake Formation, IAM, S3 e KMS também não está
declarada como tipo no grafo de permissão. Ver [`known-unknowns.md`](known-unknowns.md).

**Isto encolheu em 2026-09-09, e a conclusão não.** A família `SF-ERR-014` a `SF-ERR-017`
passou a distinguir em qual **plano** a operação parou — credencial vendida, ação de IAM
sobre a API do Glue, ou validação do isolamento do system driver. O que continua não
existindo é a permissão em si: nenhuma concessão do Lake Formation, nenhuma policy de IAM e
nenhum registro de localização S3 entra em artefato que este motor colete. Um achado da área
diz onde a operação parou; ele não diz qual permissão falta, e
`lakeformation.unresolved` publica essa distância em vez de escondê-la.

Também não existe coleta do **grant** nem da **policy**. Um verbo de coleta para os dois é a
próxima peça óbvia desta área, e enquanto ele não existir toda recomendação de permissão sai
como leitura a fazer, nunca como conserto verificado.
