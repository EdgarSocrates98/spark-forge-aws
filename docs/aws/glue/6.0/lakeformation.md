# Lake Formation com controle de acesso fino (FGAC)

Conhecimento completo — o que FGAC exige, o que ele proíbe, o que ele custa em capacidade e o
recorte próprio de Iceberg — em
[`../../../../knowledge/glue/lakeformation-fgac.md`](../../../../knowledge/glue/lakeformation-fgac.md).
Este documento não repete as tabelas de lá; ele diz o que o SparkForge faz com elas.

Ligar FGAC num job Glue não é conceder uma permissão e esquecer: muda **o que o job pode
ser**. Parte do que era código legítimo passa a ser bloqueada, e parte da capacidade paga
deixa de rodar trabalho do usuário.

## A área `SF-LF`

`rules/catalog/lakeformation.yaml` declara a área **`SF-LF`**, com duas
incompatibilidades **declaradas pela AWS** — não inferidas:

| Regra | O que ela acusa |
|---|---|
| `SF-LF-001` | JAR adicional declarado num job com FGAC habilitado |
| `SF-LF-002` | FGAC habilitado num job de streaming |

As duas nascem da mesma fronteira: o Glue **bloqueia** fornecimento de JAR adicional para
preservar o isolamento completo do system driver, e streaming está na lista de não
suportados. Um job que declara as duas coisas ao mesmo tempo está pedindo duas coisas que a
AWS declara incompatíveis.

O sinal de FGAC é o job parameter `--enable-lakeformation-fine-grained-access`. Não é
propriedade do recurso Terraform nem configuração de sessão Spark: é argumento de job, e vive
junto do resto dos `default_arguments`.

## Três coisas que o desenho costuma errar

**Escrita não passa pelo Lake Formation.** Escrever numa tabela Lake Formation usa permissão
**IAM**, não as permissões concedidas no Lake Formation. Quem escreve é o runtime role do
job, com as permissões S3 dele. Um modelo de governança que assuma "FGAC cobre leitura e
escrita" está errado sobre a metade da escrita.

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
