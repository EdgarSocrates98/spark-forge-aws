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

## Fontes

- Iceberg Table Spec (tag 1.11.0). https://raw.githubusercontent.com/apache/iceberg/apache-iceberg-1.11.0/format/spec.md (retrieved 2026-08-22)
- Apache Iceberg 1.11.0 release. https://github.com/apache/iceberg/releases/tag/apache-iceberg-1.11.0 (retrieved 2026-08-22)
- Migrating AWS Glue for Spark jobs to AWS Glue version 6.0. https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html (retrieved 2026-08-22)
- Custo de leitura, pruning e efeito de shredding sobre o plano em colunas VARIANT não foram lidos nesta coleta. A verificar.
- Alcance exato do suporte inicial a `MERGE INTO` com evolução de schema no Spark 4.1 não foi lido nesta coleta. A verificar.
