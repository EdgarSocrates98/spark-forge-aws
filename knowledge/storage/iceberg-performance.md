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

### Como saber quais arquivos são anteriores ao sort order atual

Pergunta operacional direta — "já defini o sort order, quanto do passivo ainda não se beneficia dele?" — e a resposta é menos disponível do que parece. Investigado em 2026-07-30 contra a spec e o código do Iceberg; é o que sustenta `SF-ICE-004`.

**O que NÃO responde:**

| Fonte | Por que não serve |
|---|---|
| `metadata-log` do `metadata.json` | Cada entrada tem exatamente dois campos, `metadata-file` e `timestamp-ms`. Não carrega sort order. Datar a mudança por aí exige baixar e parsear cada `metadata.json` histórico — e `write.metadata.previous-versions-max` (default 100) mais `write.metadata.delete-after-commit.enabled` podem já ter apagado os relevantes. |
| `snapshots` / `.history` | O snapshot registra `schema-id` e **não** registra `sort-order-id`. A assimetria é da própria spec, em v1, v2 e v3. Não existe "qual sort order valia no snapshot N". |
| `.metadata_log_entries` | Expõe `timestamp`, `file`, `latest_snapshot_id`, `latest_schema_id`, `latest_sequence_number`. De novo: schema sim, sort order não. E a metadata table só existe a partir do **Iceberg 1.1.0** — não está em 1.0.0 (Glue 4.0). |
| `.files` para ligar arquivo a snapshot | Nenhuma das tabelas `files`/`all_data_files` tem coluna de snapshot. Só `entries`/`all_entries` (`snapshot_id`) e `manifests` (`added_snapshot_id`) fazem essa ligação — e o Athena não expõe `$entries`. |

**O que responde, com um limite duro:** o campo 140 do struct `data_file`, `sort_order_id` (`int`, opcional), presente desde o formato v1 e exposto como coluna pelas metadata tables `files`/`data_files`/`all_data_files` (elas derivam o schema de `DataFile.getType`, então expõem todo campo do struct).

- `sort_order_id` **não-zero e diferente** do `default-sort-order-id` → o arquivo foi escrito sob outra ordem registrada. **Prova**, porque id não-zero só existe quando um writer chamou `withSortOrder` com uma ordem de `sort-orders`.
- `sort_order_id` **igual** ao `default-sort-order-id` (não-zero) → escrito sob a ordem vigente. Também prova.
- `sort_order_id == 0` → **não prova nada.** Ver abaixo.

### A armadilha do `sort_order_id = 0` em Glue

`DataFiles.Builder` inicializa `sortOrderId = SortOrder.unsorted().orderId()`, ou seja **0**. O writer do Spark só passou a sobrescrever esse default no **Iceberg 1.11.0**, quando `SparkWrite.java` ganhou `.dataSortOrder(table.sortOrders().get(sortOrderId))` e a opção `output-sort-order-id`. Nas tags **1.7.1** e **1.10.0** não há nenhuma menção a sort order no mesmo arquivo.

| Glue | Iceberg | Spark grava `sort_order_id`? |
|---|---|---|
| 4.0 | 1.0.0 | não |
| 5.0 | 1.7.1 | não |
| 5.1 | 1.10.0 | não |
| — | 1.11.0+ | sim, condicionalmente |

Consequência prática: **em qualquer runtime Glue de hoje, todo data file escrito pelo Spark sai com `sort_order_id = 0`** — inclusive os recém-produzidos por um `rewrite_data_files` com estratégia `sort` que de fato ordenou os dados. Um relatório que leia esse 0 como "arquivo não ordenado" acusa toda tabela Iceberg escrita por Glue, incluindo as que acabaram de ser compactadas, e cada acusação dessas custa um `rewrite_data_files` sobre tabela grande.

Mesmo em 1.11+ o campo só é gravado quando a ordem do job **casa com uma ordem já registrada** em `sort-orders`: um `rewrite_data_files` com `sort_order => 'col ASC'` ad-hoc, ou um `zorder`, produz 0 com um WARN no driver.

Por isso `0` e coluna ausente são tratados como **a mesma coisa — desconhecido** — em `sparkforge/facts/iceberg_metadata.py`, e `SF-ICE-004` só dispara com evidência de ordem registrada anterior. Numa tabela escrita só por Glue, a regra fica calada por falta de evidência, não por ausência de passivo, e isso aparece como `iceberg.unresolved` com reason `sort_order_id_missing`.

**Como medir o passivo mesmo assim, em Glue:** não pelo metadado. Meça bytes lidos por uma query de referência filtrando a coluna de sort, antes e depois do rewrite; ou compare a sobreposição de `lower_bounds`/`upper_bounds` daquela coluna entre os data files em `.files` — arquivos com faixas muito sobrepostas não estão agrupados, independentemente do que o `sort_order_id` diga.

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
| `.metadata_log_entries` | crescimento dos metadata files — **só a partir do Iceberg 1.1.0**, não existe em Glue 4.0 |
| `.entries` / `.all_entries` | única forma de ligar um data file ao snapshot que o adicionou (`snapshot_id`, `status`); o Athena não expõe `$entries` |

Sequência de diagnóstico: `.files` (tamanho médio vs. 128–512 MB) → `.delete_files` (dívida MoR) → `.snapshots` (frequência de commit) → `.manifests` (custo de planejamento) → `.partitions` (skew e cardinalidade).

Como o Glue **não** emite métrica de escrita para Iceberg (ver `../cross-service-constraints.md` §2), essas metadata tables são a única fonte quantitativa de escrita. Não são opcionais no diagnóstico.

## Fontes

- Spark Procedures — Apache Iceberg. https://iceberg.apache.org/docs/latest/spark-procedures/ (retrieved 2026-07-29) — **doc `latest`; confirmar contra a versão embarcada**
- New — Improve Apache Iceberg query performance in Amazon S3 with sort and Z-order compaction. https://aws.amazon.com/blogs/aws/new-improve-apache-iceberg-query-performance-in-amazon-s3-with-sort-and-z-order-compaction (retrieved 2026-07-29)
- Introducing AWS Glue 5.1 for Apache Spark (Iceberg 1.10.0: format V3, deletion vectors, transforms multi-argumento, row lineage). https://aws.amazon.com/blogs/big-data/introducing-aws-glue-5-1-for-apache-spark (retrieved 2026-07-29)
- Iceberg Table Spec, tag `apache-iceberg-1.0.0` (campo 140 `sort_order_id`; "Order id `0` is reserved for the unsorted order"; `metadata-log` com apenas `metadata-file` e `timestamp-ms`; snapshot sem `sort-order-id`). https://github.com/apache/iceberg/blob/apache-iceberg-1.0.0/format/spec.md (retrieved 2026-07-30) — **tag 1.0.0 de propósito: é a versão mais antiga do range Glue suportado**
- `DataFiles.java`, tag `apache-iceberg-1.10.0` (`private Integer sortOrderId = SortOrder.unsorted().orderId();`). https://github.com/apache/iceberg/blob/apache-iceberg-1.10.0/core/src/main/java/org/apache/iceberg/DataFiles.java (retrieved 2026-07-30)
- `SparkWrite.java` nas tags `apache-iceberg-1.7.1` e `apache-iceberg-1.10.0` (sem `dataSortOrder`) contra `apache-iceberg-1.11.0` (com `dataSortOrder` e `output-sort-order-id`). https://github.com/apache/iceberg/blob/apache-iceberg-1.11.0/spark/v3.5/spark/src/main/java/org/apache/iceberg/spark/source/SparkWrite.java (retrieved 2026-07-30)
- Inspecting tables — Apache Iceberg Spark Queries (colunas de `files`, `entries`, `metadata_log_entries`). https://iceberg.apache.org/docs/latest/spark-queries/#inspecting-tables (retrieved 2026-07-30) — doc `latest`; a disponibilidade por versão de `metadata_log_entries` (1.1.0+) foi verificada em `MetadataTableType.java` nas tags
- Compaction in Apache Iceberg — Dremio. https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/ (retrieved 2026-07-29)
- Alvo de ~512 MB para `write.target-file-size-bytes` em Parquet é recomendação de campo, não normativa.
- Comportamento exato de `write.distribution-mode` por versão não foi reconfirmado nesta coleta. Verificar antes de recomendar valor específico.
