# Apache Iceberg — performance e manutenção

Confirmar a versão embarcada antes de usar qualquer API: Glue 4.0 → 1.0.0, Glue 5.0 → 1.7.1, Glue 5.1 → 1.10.0. Ver `../glue/runtime-matrix.md`.

## 1. As cinco camadas que precisam ser distinguidas

Tratar tudo como "arquivo Iceberg" é a causa de manutenção errada.

| Camada | O que é | Sintoma quando degrada | Correção |
|---|---|---|---|
| **Data files** | Parquet com as linhas | small files; leitura lenta | `rewrite_data_files` (compactação) |
| **Delete files** | marcas de linha deletada (merge-on-read) | leitura progressivamente mais lenta sem mudança de query | `rewrite_data_files` com reconciliação; revisar estratégia MoR vs CoW |
| **Manifests** | listas de data files + estatísticas de partição | planejamento lento; driver heap alto | `rewrite_manifests` |
| **Snapshots** | versões da tabela | metadados crescendo; `metadata.json` grande | `expire_snapshots` (**destrutivo**) |
| **Metadata files** | `metadata.json`, version hint | planejamento lento no commit | `write.metadata.delete-after-commit.enabled` |

Distinção que muda a ação: **planejamento lento** aponta para manifests/snapshots/metadata. **Leitura lenta** aponta para data files/delete files. Compactar dados quando o problema é manifest não resolve nada e custa horas de DPU.

## 2. Propriedades de tabela que importam

| Propriedade | Efeito |
|---|---|
| `write.target-file-size-bytes` | Tamanho-alvo dos data files na escrita e no rewrite. Alvo usual em Parquet: ~512 MB |
| `write.distribution-mode` | `none` / `hash` / `range` — controla o shuffle antes da escrita; determina quantos arquivos por partição |
| `write.format.default` | formato dos data files |
| `write.parquet.compression-codec` | codec |
| `write.metadata.delete-after-commit.enabled` | remove metadata files antigos automaticamente |
| `write.metadata.previous-versions-max` | quantas versões de metadata manter |
| `format-version` | **2 ou 3.** V3 não é legível por Athena — ver `../cross-service-constraints.md` |
| `commit.retry.num-retries` | resiliência a commit concorrente |

`write.distribution-mode` é a propriedade mais subestimada. Com `none`, cada task escreve na sua partição → N tasks × M partições = N×M arquivos. Com `hash` ou `range`, há shuffle antes da escrita e o número de arquivos cai drasticamente. É a correção estrutural de small files em Iceberg, feita **na escrita**, em vez de compactar depois.

## 3. Partition spec e sort order

Iceberg tem **hidden partitioning**: a partição é derivada por transform da coluna, e a query não precisa filtrar pela coluna derivada.

Transforms: `identity`, `bucket[N]`, `truncate[W]`, `year`, `month`, `day`, `hour`. Iceberg 1.10 adiciona transforms multi-argumento.

| Decisão | Regra |
|---|---|
| Partição | coluna de filtro de **baixa** cardinalidade e alta seletividade (data) |
| `bucket[N]` | chave de alta cardinalidade usada em join/lookup; N fixa o número de buckets |
| Sort order | coluna de filtro de **alta** cardinalidade — aperta min/max dos row groups |

**Partition evolution** existe: mudar o spec não reescreve dados antigos. Arquivos antigos mantêm o spec antigo, e a tabela passa a ter specs mistos. Isso é uma capacidade, e também uma dívida: o planejamento passa a lidar com dois layouts. Mudar spec sem plano para os dados antigos deixa a tabela permanentemente mais lenta de planejar.

Sort order só afeta **escritas futuras** e o `rewrite_data_files` com estratégia de sort. Definir sort order numa tabela existente sem rodar rewrite não muda nada nos dados já gravados.

## 4. Copy-on-write vs. merge-on-read

| | Copy-on-write | Merge-on-read |
|---|---|---|
| Update/delete | reescreve os data files afetados | grava delete files |
| Custo de escrita | alto | baixo |
| Custo de leitura | baixo | cresce com delete files acumulados |
| Adequado a | leitura frequente, escrita rara | escrita frequente, com compactação regular |

MoR sem compactação regular é uma armadilha de degradação lenta: cada leitura reconcilia mais delete files, e a query fica mais lenta a cada semana sem que nada tenha mudado. Iceberg 1.10 introduz **deletion vectors** para MoR, mudando esse trade-off — verificar disponibilidade na versão do runtime.

## 5. Procedimentos de manutenção

Sintaxe e parâmetros **variam por versão**. Confirmar na doc da versão embarcada.

| Procedimento | Função | Destrutivo |
|---|---|---|
| `rewrite_data_files` | compacta data files; suporta estratégia `sort` e `zorder` | não (mas reescreve) |
| `rewrite_manifests` | reorganiza manifests | não |
| `rewrite_position_delete_files` | compacta delete files | não |
| `expire_snapshots` | remove snapshots antigos e seus arquivos | **sim** |
| `remove_orphan_files` | remove arquivos não referenciados | **sim** |

### Regra de segurança

`expire_snapshots` e `remove_orphan_files` **destroem** capacidade de time travel e podem remover arquivos em uso por leitores concorrentes ou por escritas em andamento.

Nunca executar sem:
1. Escopo explícito (qual tabela, qual retenção).
2. Retenção acordada com o negócio (time travel é requisito em alguns domínios).
3. Confirmação explícita do operador.
4. Dry run quando a versão suportar.
5. Plano de rollback — sabendo que, para esses dois, **não há rollback**.

`remove_orphan_files` com janela de tempo curta pode apagar arquivos de uma escrita em andamento. A janela default existe por esse motivo; reduzi-la é decisão de risco.

## 6. Compactação com sort e Z-order

`rewrite_data_files` aceita estratégia:

- **binpack** (default): só junta arquivos. Resolve contagem, não pruning.
- **sort**: reordena por colunas especificadas. Aperta min/max → melhora pruning futuro.
- **zorder**: ordena por múltiplas colunas simultaneamente. Para quando os filtros variam entre duas ou três colunas.

`sort_order` no procedimento aceita direção e tratamento de null, ex.: `'id DESC NULLS LAST, nome ASC NULLS FIRST'`.

Escolha: binpack se o problema é contagem de arquivos; sort se o problema é pruning e há uma coluna de filtro dominante; zorder se há duas ou três colunas de filtro concorrentes. Zorder custa mais e não é gratuito — só com evidência de filtros multi-coluna.

## 7. Commits, snapshots e o loop de append

Cada commit cria um snapshot. Um loop com 500 appends cria 500 snapshots, com manifests correspondentes.

Efeitos: `metadata.json` cresce; planejamento de leitura carrega mais metadado; risco de conflito de commit concorrente; driver heap subindo ao longo do run (ver `../spark/memory-and-oom.md` §3).

Correções, em ordem: escrever uma vez em vez de por lote; agrupar lotes antes do commit; separar full, incremental e manutenção em jobs distintos; `expire_snapshots` regular com retenção definida.

## 8. Diagnóstico via metadata tables

Queries em `../iceberg-diagnostics.sql`. O que cada uma responde:

| Tabela | Pergunta |
|---|---|
| `.files` | quantos data files, tamanho médio/p50/p95, distribuição por partição |
| `.delete_files` | quantos delete files, e por partição — mede dívida de MoR |
| `.snapshots` | quantos snapshots, com que frequência, desde quando |
| `.manifests` | quantos manifests, tamanho, quantos data files cada um cobre |
| `.partitions` | contagem de arquivos e linhas por partição — mede skew de partição |
| `.history` | linhagem de snapshots, para time travel e auditoria |
| `.metadata_log_entries` | crescimento dos metadata files |

Sequência de diagnóstico: `.files` (tamanho médio vs. 128–512 MB) → `.delete_files` (dívida MoR) → `.snapshots` (frequência de commit) → `.manifests` (custo de planejamento) → `.partitions` (skew e cardinalidade).

Como o Glue **não** emite métrica de escrita para Iceberg (ver `../cross-service-constraints.md` §2), essas metadata tables são a única fonte quantitativa de escrita. Não são opcionais no diagnóstico.

## Fontes

- Spark Procedures — Apache Iceberg. https://iceberg.apache.org/docs/latest/spark-procedures/ (retrieved 2026-07-29) — **doc `latest`; confirmar contra a versão embarcada**
- New — Improve Apache Iceberg query performance in Amazon S3 with sort and Z-order compaction. https://aws.amazon.com/blogs/aws/new-improve-apache-iceberg-query-performance-in-amazon-s3-with-sort-and-z-order-compaction (retrieved 2026-07-29)
- Introducing AWS Glue 5.1 for Apache Spark (Iceberg 1.10.0: format V3, deletion vectors, transforms multi-argumento, row lineage). https://aws.amazon.com/blogs/big-data/introducing-aws-glue-5-1-for-apache-spark (retrieved 2026-07-29)
- Compaction in Apache Iceberg — Dremio. https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/ (retrieved 2026-07-29)
- Alvo de ~512 MB para `write.target-file-size-bytes` em Parquet é recomendação de campo, não normativa.
- Comportamento exato de `write.distribution-mode` por versão não foi reconfirmado nesta coleta. Verificar antes de recomendar valor específico.
