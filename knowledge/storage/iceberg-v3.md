# Apache Iceberg 1.11 e o formato v3

Este documento tem duas metades, e a separação entre elas é a razão de ele existir:

1. **Feature da spec** — o que o formato v3 define, lido do `format/spec.md` da tag
   `apache-iceberg-1.11.0`, mais o que a biblioteca 1.11.0 passou a implementar.
2. **Suporte da engine** — o que o AWS Glue 6.0 declara suportar, lido de
   `migrating-version-60.html`.

**As duas não se deduzem uma da outra.** "A spec v3 define transforms multi-argumento"
não implica "o Glue 6.0 executa transforms multi-argumento" — neste caso específico ela
implica o contrário, porque a AWS declara essa limitação por escrito. Toda vez que uma
recomendação atravessar da metade 1 para a metade 2 sem uma linha da metade 2 que a
sustente, a recomendação é inferência, não fato.

Versões embarcadas por runtime em [`../glue/runtime-matrix.md`](../glue/runtime-matrix.md).
Performance e manutenção de tabela em
[`iceberg-performance.md`](iceberg-performance.md).

---

## Metade 1 — Feature da spec

### 1. O que a v3 acrescenta sobre a v2

Da lista da própria spec (tag `apache-iceberg-1.11.0`):

| Capacidade | Texto da spec |
|---|---|
| Tipos novos | *"New data types: nanosecond timestamp(tz), unknown, variant, geometry, geography"* |
| Default de coluna | *"Default value support for columns"* |
| Transforms multi-argumento | *"Multi-argument transforms for partitioning and sorting"* |
| Row lineage | *"Row Lineage tracking"* |
| Deletion vectors binários | *"Binary deletion vectors"* |

Sobre o tipo variant, a spec diz apenas: *"A `variant` is a value that stores
semi-structured data."* Qualquer afirmação além disso — como o custo de leitura, o
comportamento de pruning ou o efeito de shredding no plano — **é a verificar**: não foi
lida da spec nesta coleta.

### 2. Biblioteca Iceberg 1.11.0

Release publicada em 2025-05-20. O que ela traz, do release note:

- Remote scan planning com REST catalog, incluindo implementação server-side.
- Criptografia de manifest list e rotação automática de chave de criptografia de chave.
- Deletion vectors: leitura e escrita em Flink e Spark.
- Filtro sobre tipo variant e tratamento em leitores Parquet.
- Registro de view e detecção de conflito de view no registro de tabela.
- API de scan para ler estatísticas de partição.

Duas mudanças de piso, que não são features e mordem antes delas:

| Mudança | Efeito |
|---|---|
| **Suporte a Java 11 removido** | mínimo passa a ser **Java 17** |
| **Spark 3.4 passa a deprecado** | continua funcionando, mas sem garantia futura |

Versões de Spark suportadas pela 1.11.0: **3.5, 4.0 e 4.1** — a 4.1 é nova nesta release.
Nela há **suporte inicial** a `MERGE INTO` com evolução de schema no Spark 4.1. "Inicial"
é a palavra da fonte; o alcance exato desse suporte é a verificar.

---

## Metade 2 — Suporte da engine no AWS Glue 6.0

Esta metade é lida de `migrating-version-60.html`, já vigiada em
`knowledge/sources.lock.json`. Nada aqui é deduzido da metade 1.

### 3. O que o Glue 6.0 declara suportar

Glue 6.0 traz **Iceberg 1.11.0 com suporte a v3**, e nomeia:

- VARIANT com shredding.
- Timestamps de precisão nanossegundo.
- Tipos geoespaciais.

### 4. O que já era suportado antes, e não é novidade do 6.0

Ponto que costuma ser lido errado em plano de migração:

| Capacidade | Desde |
|---|---|
| Deletion vectors (merge-on-read com Roaring Bitmap em arquivo Puffin) | **Glue 5.1** |
| Row lineage por `first-row-id` | **Glue 5.1** |

Um plano que justifique o salto para o Glue 6.0 por deletion vectors ou row lineage está
pagando uma migração por algo que o runtime anterior já entregava.

### 5. Limitações declaradas pela AWS para o Glue 6.0

Estas são o motivo pelo qual a metade 1 não pode ser usada sozinha:

| Limitação | Consequência prática |
|---|---|
| Chaves de criptografia nativa de tabela Iceberg **não suportadas** | a criptografia de manifest list da 1.11.0 não está disponível pela via nativa da tabela |
| **Transforms multi-argumento não suportados** | a feature está na spec v3 e **não** na engine; partition spec e sort order continuam de argumento único |
| Tipos novos da v3 funcionam **apenas com Spark DataFrames** | job escrito sobre **DynamicFrame** não os alcança |
| Visual ETL do Glue Studio **não suporta** os tipos novos da v3 | pipeline montado no Studio fica fora do alcance |
| FGAC (controle de acesso fino) **não suportado** com colunas VARIANT | escolha entre VARIANT e granularidade de acesso, não as duas |
| Tabela criada com `'format-version'='3'` **não pode ser lida pelo Athena SQL** | erro textual: `Cannot read unsupported version 3` |

Sobre a última: para compatibilidade entre engines, use **v2**. Essa é a única armadilha
desta página que já é judicável neste repositório — ver `SF-ENV-002` no catálogo e a §1 de
[`../cross-service-constraints.md`](../cross-service-constraints.md). Não escrever regra
nova para ela; ela já tem uma.

---

## 6. Por que este documento não vira regra ainda

O conteúdo acima é conhecimento, não motor. As três armadilhas novas — Variant sob FGAC,
transform multi-argumento e tipo v3 sob DynamicFrame — **não têm fact que as sustente**
neste repositório, e regra sem fact é regra que nunca dispara ou que dispara por chute.
O que faltaria, nomeado:

| Julgamento desejado | Fact que não existe |
|---|---|
| Uso de coluna VARIANT numa tabela | tipo de coluna no schema Iceberg, com `variant` distinguível — hoje não há fact de tipo de coluna com esse vocabulário |
| Transform multi-argumento em partition spec ou sort order | aridade do transform no partition spec; o fact de partition spec de hoje não carrega os argumentos do transform |
| Job que usa DynamicFrame junto com tipo novo da v3 | marcador de uso de DynamicFrame no código do job, correlacionável com o schema da tabela escrita |
| Pipeline montado no Visual ETL do Glue Studio | procedência do job (Studio contra script), que a definição do job hoje não expõe como fact |

Criar extrator para qualquer um deles **antes** de haver consumidor é exatamente o erro
que `docs/harness/GLUE6-GAP.md` existe para impedir. A ordem correta é: fact primeiro
quando houver julgamento que o consuma, não o inverso.

A armadilha do format-version 3 contra Athena, essa sim, já é judicável — e já é
`SF-ENV-002`, lendo `iceberg.table_property` com `format-version = 3` junto de
`env.consumer` com `service: athena`. Duplicá-la seria dívida, não cobertura.

## 7. A mesma separação como dado consultável

A separação entre as duas metades deste documento existe também como dado, em
[`iceberg-feature-support.yaml`](iceberg-feature-support.yaml), carregado por
`sparkforge/storage/feature_support.py`. O YAML é uma matriz de **13 features contra 14
engines** (`glue`, `athena`, `emr_ec2`, `emr_serverless`, `emr_eks`, `redshift`, `trino`,
`spark`, `flink`, `pyiceberg`, `bigquery`, `rest_client`, `s3_tables`, `lakeformation`) em
que **cada célula carrega a própria evidência** — e o carregador recusa a matriz inteira se
alguma célula afirmar suporte sem `source`, `source_type` e `retrieved`.

`UNKNOWN` é o único status que dispensa fonte, e é o status da maioria das células: **174
das 191**. Isso não é lacuna do dado, é o resultado honesto de só existir documentação
oficial enumerando feature de v3 por nome para uma engine. A alternativa — preencher a linha
do Athena a partir do que o Iceberg suporta — é a inferência que a metade 1 deste documento
proíbe, e agora há um teste que falha quando ela acontece.

O Athena tem **três células preenchidas**, e as três vêm de **páginas diferentes**:
`variant` (`UNSUPPORTED`, da página de migração do Glue 6.0), `merge_into` (`PARTIAL`, da
página de atualização de dado do Athena) e `schema_evolution` (`PARTIAL`, da página de
evolução de schema). A frase da seção 5 fala do *formato da tabela*, não de cada feature;
estendê-la para as outras seis features da v3 fabricaria célula por raciocínio, que é o mesmo
defeito na direção negativa. O que se sabe e não sustenta célula mora em
`engines.athena.note`, dentro do YAML.

Um caso vale ser lido junto com a seção 5: `multi_argument_transforms` é `UNSUPPORTED` no
Glue 6.0 **apesar** de estar na spec v3. É a linha em que a spec implica o contrário da
engine.

## 8. `emr` não é uma engine, e por que isso mudou a matriz

Até 2026-09-01 a matriz tinha uma única linha `emr`. As três plataformas publicam Iceberg
**diferente** — divergência em **6 de 26** releases comparáveis entre EC2 e EKS, medida em
[`../emr-eks/runtime-matrix.md`](../emr-eks/runtime-matrix.md):

| release | EMR on EC2 | EMR on EKS |
|---|---|---|
| `emr-7.7.0` | `1.7.1-amzn-0` | `1.6.1-amzn-2` |
| `emr-6.5.0` | `0.12.0` | *nenhum Iceberg publicado* |

Uma resposta de prontidão dada para "EMR" está errada para pelo menos uma das três, e o
operador não tem como saber qual. Célula que responde por três coisas que divergem é pior que
célula ausente: ausência é recusa, e aquela célula era uma afirmação. Hoje são `emr_ec2`,
`emr_serverless` e `emr_eks`.

**A versão de Iceberg não foi copiada para cá.** Ela já mora em
`knowledge/<plataforma>/runtime-matrix.yaml` e uma coluna aqui seria a terceira cópia do mesmo
fato. O que a matriz de feature declara é `min_library_version` — a partir de qual release da
**biblioteca** a capacidade aparece, com a citação exata das notas curadas do Apache Iceberg —
e `sparkforge/storage/readiness.py` calcula o cruzamento.

`min_library_version` é **limite inferior**, nunca prova de suporte:

- biblioteca **anterior** ao mínimo → `UNSUPPORTED`. Uma biblioteca publicada antes da
  primeira release que nomeia a capacidade não pode tê-la.
- biblioteca **atende** o mínimo → **não** vira `SUPPORTED`. O resultado é o que a célula da
  engine disser, que quase sempre é `UNKNOWN`. Atender é condição necessária, nunca
  suficiente: a AWS repackaga (`-amzn-N`) e pode desabilitar o que a upstream entrega.

O efeito é conferível em `emr-7.7.0`, com `nanosecond_timestamp` (mínimo `1.7.0`):

| plataforma | Iceberg | resposta | razão |
|---|---|---|---|
| `emr_ec2` | `1.7.1-amzn-0` | `UNKNOWN` | `biblioteca_atende_o_minimo` |
| `emr_serverless` | — | `UNKNOWN` | `iceberg_ausente_na_release` |
| `emr_eks` | `1.6.1-amzn-2` | `UNSUPPORTED` | `biblioteca_anterior_ao_minimo` |

**O limite da granularidade está declarado.** A linha de componentes do EMR on EKS é publicada
por *família*, não por variante de imagem: a própria fonte diz que `emr-7.7.0-java8-latest`
**não** tem Iceberg enquanto `emr-7.7.0` tem. Perguntar por um label com variante devolve
`UNKNOWN` com a razão `variante_de_imagem_fora_da_matriz`, nunca a resposta da família.

## 9. IAM não é prova de acesso ao dado

Lake Formation, S3, KMS e Glue Catalog são camadas **separadas**: uma feature pode ser
suportada pela engine e inalcançável pela FGAC. As quatro combinações que o prompt mestre
nomeia, e o estado de cada uma nesta coleta:

| combinação | estado | fonte |
|---|---|---|
| `VARIANT × FGAC` | **confirmado** — FGAC não é suportado com coluna VARIANT | migração do Glue 6.0 |
| `DELETE/MERGE × FGAC` | **confirmado** — Lake Formation não gerencia permissão para `VACUUM`, `MERGE`, `UPDATE` ou `OPTIMIZE` em Iceberg | Iceberg no Athena |
| `v3 × FGAC` | `UNKNOWN` — nenhuma fonte lida fala de FGAC contra o **formato** da tabela | — |
| `REST Catalog × Lake Formation` | `UNKNOWN` — a página do endpoint Iceberg REST do Glue não menciona Lake Formation | — |

Uma quinta afirmação lida é sobre **metadata** e não sobre feature: com filtro de linha ou de
célula do Lake Formation na tabela base, as metadata tables `$partitions`, `$files`,
`$manifests` e `$snapshots` e a coluna `$path` falham com `AccessDeniedException` no Athena.
É o caso limpo de "a engine suporta, e a camada de governança não deixa chegar ao dado".

## Fontes

- Iceberg Table Spec (tag 1.11.0). https://raw.githubusercontent.com/apache/iceberg/apache-iceberg-1.11.0/format/spec.md (retrieved 2026-08-22)
- Apache Iceberg 1.11.0 release. https://github.com/apache/iceberg/releases/tag/apache-iceberg-1.11.0 (retrieved 2026-08-22)
- Migrating AWS Glue for Spark jobs to AWS Glue version 6.0. https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html (retrieved 2026-08-22)
- Iceberg release history (Amazon EMR). https://docs.aws.amazon.com/emr/latest/ReleaseGuide/Iceberg-release-history.html (retrieved 2026-08-22)
- Notas curadas por release do Apache Iceberg (tag 1.11.0), fonte de `min_library_version`. https://raw.githubusercontent.com/apache/iceberg/apache-iceberg-1.11.0/site/docs/releases.md (retrieved 2026-09-01)
- Query Apache Iceberg tables (Amazon Athena): considerações, limitações e as duas afirmações sobre Lake Formation. https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg.html (retrieved 2026-09-01)
- Update Iceberg table data (Amazon Athena): `INSERT`/`UPDATE`/`DELETE`/`MERGE INTO` e o recorte de merge-on-read. https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg-updating-iceberg-table-data.html (retrieved 2026-09-01)
- Evolve Iceberg table schema (Amazon Athena): as mudanças de schema e as DDL que o Athena expõe. https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg-evolving-table-schema.html (retrieved 2026-09-01)
- Connecting to the Data Catalog using AWS Glue Iceberg REST endpoint: as especificações suportadas e as operações REST expostas. https://docs.aws.amazon.com/glue/latest/dg/connect-glu-iceberg-rest.html (retrieved 2026-09-01)
- Custo de leitura, pruning e efeito de shredding sobre o plano em colunas VARIANT não foram lidos nesta coleta. A verificar.
- Alcance exato do suporte inicial a `MERGE INTO` com evolução de schema no Spark 4.1 não foi lido nesta coleta. A verificar.
- `variant_shredding` e `multi_argument_transforms` ficaram **sem** `min_library_version`: as notas curadas de 1.6.0 a 1.10.1 não nomeiam nenhuma das duas em release alguma. A medida que destrava é a nota curada de 1.11.0, que não está no `releases.md` da própria tag 1.11.0. A verificar.
- Nenhuma fonte de feature de Iceberg foi lida para `emr_ec2`, `emr_serverless`, `emr_eks`, `redshift`, `trino`, `spark`, `flink`, `pyiceberg`, `bigquery` e `s3_tables`: as células de engine dessas dez continuam `UNKNOWN`, e o que responde por três delas é o cruzamento por release. A verificar.
