# Amazon Athena — performance e custo

Adição de escopo ao SparkForge (2026-07-29). Athena não era coberta pelas 18 skills originais. Entra porque, num lakehouse Glue + Iceberg, Athena costuma ser o **consumidor** — e decisões tomadas no job Glue determinam o custo e a viabilidade da query em Athena.

## 1. Modelo de custo

Athena (SQL padrão, serverless) cobra por **bytes escaneados**. Não por tempo, não por CPU.

Consequências diretas:

| Alavanca | Efeito nos bytes escaneados |
|---|---|
| Formato colunar (Parquet/ORC) vs. linha (CSV/JSON) | reduz drasticamente — só as colunas do `SELECT` são lidas |
| `SELECT *` vs. colunas explícitas | `SELECT *` anula o benefício colunar |
| Partition pruning efetivo | reduz proporcionalmente à seletividade |
| Compressão | reduz bytes lidos |
| Arquivos grandes vs. small files | pouco efeito em *bytes*, muito em *latência* |
| `LIMIT` sem `WHERE` | **não reduz** bytes escaneados de forma confiável |

O último item derruba a intuição mais comum: `SELECT * FROM tabela LIMIT 10` pode escanear a tabela inteira. `LIMIT` não é filtro.

`SELECT *` num data lake colunar é o anti-pattern de custo número um em Athena, e é invisível para quem só olha duração.

Ganhos reportados de formato colunar vs. row-based: 85–90% de redução. Tratar como ordem de grandeza dependente do número de colunas realmente usadas, não como constante.

## 2. Engine version 3

Ganhos sobre v2: execução mais rápida, otimização dinâmica de memória, melhor performance de JOIN, **dynamic filtering**, melhor integração com metadados do Glue Catalog, mais funções SQL, e suporte otimizado a Iceberg.

Implicação para diagnóstico: query lenta em Athena deve começar por **confirmar a engine version do workgroup**. Recomendar reescrita de SQL antes de verificar isso é tuning às cegas — dynamic filtering na v3 resolve sozinho parte dos casos de join que a v2 exigia reescrever à mão.

## 3. Partitioning e partition projection

### Hive-style partitioning

Athena consulta o Glue Catalog para resolver quais partições existem, **antes** de escanear. Com centenas de milhares a milhões de partições, essa resolução de metadados vira o gargalo — a query fica lenta mesmo escaneando pouco dado.

Sintoma: latência alta e constante independente da seletividade do `WHERE`, com bytes escaneados baixos.

### Partition projection

Define o **padrão** das partições nas table properties. Athena calcula matematicamente quais partições existem, sem consultar o catálogo.

Ganhos: elimina o lookup de metadados por query; dispensa `MSCK REPAIR TABLE` e `ALTER TABLE ADD PARTITION`.

Quando usar: layout **denso e previsível** — partição por data contínua, por ID em range conhecido, por enum fixo.

Quando **não** usar: layout esparso (muitas partições do padrão não existem). Athena assume que existem e tenta ler; a query lê a menos partições relevantes ao `WHERE`, mas o padrão errado gera trabalho inútil e resultado incompleto se o range estiver mal definido.

Custo escondido: o range projetado precisa ser mantido. Range de data que termina em 2026 e não é atualizado faz partições novas desaparecerem silenciosamente das queries — falha por dado faltante, não por erro.

## 4. Iceberg via Athena

Athena lê tabelas Iceberg registradas no Glue Data Catalog. Restrições que decidem arquitetura:

- **Athena não lê Iceberg format version 3.** Glue 5.1 pode escrever V3. Se Athena consome a tabela, fixe `format-version = 2` ou permaneça em Glue 5.0.
- Dívida de metadados Iceberg (muitos snapshots, manifests, delete files) degrada o **planejamento** da query em Athena, não só no Spark. Manutenção de tabela é requisito do consumidor, não só do produtor.
- Delete files de merge-on-read impõem custo de reconciliação em cada leitura. Muitos delete files acumulados = queries progressivamente mais lentas sem que nada tenha mudado na query.

Ver [`../cross-service-constraints.md`](../cross-service-constraints.md).

## 5. CTAS e INSERT INTO

`CREATE TABLE AS SELECT` em Athena serve para: converter formato (CSV → Parquet), reparticionar, e materializar resultado intermediário caro.

Cuidados:
- CTAS tem limite de partições por execução. Conversão de tabela muito particionada precisa ser feita em lotes com `INSERT INTO`.
- CTAS controla formato, compressão e particionamento via `WITH (...)` — usar explicitamente, não confiar em default.
- CTAS repetido gera small files. Definir `bucketed_by`/`bucket_count` ou aceitar compactação posterior.

## 6. O que o job Glue deve fazer pensando em Athena

Esta é a ponte que costuma faltar:

| Decisão no Glue | Efeito no consumo por Athena |
|---|---|
| Escrever Parquet em vez de CSV/JSON | reduz custo de toda query futura |
| Particionar pela coluna dos filtros reais | habilita pruning; sem isso, pruning é impossível |
| Cardinalidade de partição adequada | partição de baixa cardinalidade não filtra; de altíssima cardinalidade explode metadados |
| Compactar arquivos pequenos | reduz latência de planejamento |
| Sort order alinhado aos filtros | aperta estatísticas de coluna → melhor pruning de row group |
| Fixar `format-version = 2` no Iceberg | mantém a tabela legível por Athena |
| Manutenção Iceberg (expirar snapshots, compactar) | mantém planejamento rápido para o consumidor |

A escolha de coluna de partição no job Glue é uma decisão de custo de Athena, tomada meses antes. Revisar `partitionBy` sem saber quais filtros o consumidor usa é revisar metade do problema.

## 7. Diagnóstico de query lenta ou caro

Ordem:

1. Bytes escaneados vs. tamanho da tabela — mede o pruning efetivo.
2. Engine version do workgroup.
3. `SELECT *` no SQL.
4. Filtro sobre coluna de partição, com tipo compatível (o mesmo problema de `cast` de `../spark/execution-model.md` §3).
5. Contagem de partições da tabela e se há partition projection.
6. Contagem e tamanho médio de arquivo.
7. Para Iceberg: contagem de snapshots, manifests e delete files.
8. Formato e compressão.
9. Só então: reescrita de SQL (ordem de join, subquery vs. CTE, funções de janela).

Passo 1 é o único que dá a razão de custo direto e deve vir sempre primeiro.

## Fontes

- Partition your data — Amazon Athena. https://docs.aws.amazon.com/athena/latest/ug/partitions.html (retrieved 2026-07-29)
- Top 10 performance tuning tips for Amazon Athena — AWS Big Data Blog. https://aws.amazon.com/blogs/big-data/top-10-performance-tuning-tips-for-amazon-athena (retrieved 2026-07-29)
- Run queries 3x faster with up to 70% cost savings on the latest Amazon Athena engine. https://aws.amazon.com/blogs/big-data/run-queries-3x-faster-with-up-to-70-cost-savings-on-the-latest-amazon-athena-engine (retrieved 2026-07-29)
- Restrição Iceberg V3 × Athena: Introducing AWS Glue 5.1 for Apache Spark. https://aws.amazon.com/blogs/big-data/introducing-aws-glue-5-1-for-apache-spark (retrieved 2026-07-29)
- Percentuais de ganho (85–90% colunar, 3× / 70% engine v3) vêm de material AWS e de terceiros. São ordem de grandeza dependente de workload — **não** citar como ganho previsto de uma mudança específica sem benchmark próprio.
- Limites exatos de partição em CTAS não foram reconfirmados nesta coleta. Verificar na documentação antes de citar número.
